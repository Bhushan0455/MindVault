from copy import deepcopy
from dataclasses import replace
import json
import os
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from app.services.ai_review import GeminiContentGenerator, ReviewCache, run_review
from examples.review_demo import demo_inputs


class Provider:
    """Unit-test boundary fake only; never used in production examples."""
    model="test-model"
    cache_namespace="test-model-v1"
    def __init__(self,response=None,error=None):
        self.calls=[]; self.response={"findings":[]} if response is None else response; self.error=error
    def __call__(self,payload):
        self.calls.append(deepcopy(payload))
        if self.error: raise self.error
        return deepcopy(self.response)


def tone(quote="totally awesome!"):
    return dict(category="tone",quoted_text=quote,rule_code="TONE-INV-03",fact_id=None,
        verdict="violation",severity="high",confidence=0.9,explanation="Informal wording conflicts with the investor-deck tone rule.",
        suggested_fix="available")


class AIReviewTests(unittest.TestCase):
    def setUp(self): self.inputs=demo_inputs()
    def run_service(self,provider=None,cache=None,**changes):
        return run_review(**{**self.inputs,**changes},generator=provider,cache=cache)

    def test_no_provider_returns_real_deterministic_result(self):
        r=self.run_service()
        self.assertFalse(r.ai_used)
        self.assertEqual(r.ai_status,"not_requested")
        self.assertEqual((r.findings[0].category,r.findings[0].suggested_fix),("price","₹999"))

    def test_provider_output_passes_validator_and_preserves_price(self):
        r=self.run_service(Provider({"findings":[tone()]}))
        self.assertTrue(r.ai_used)
        self.assertEqual([(f.origin,f.category) for f in r.findings],[("deterministic","price"),("ai","tone")])

    def test_foreign_pending_and_skipped_rules_never_sent(self):
        base=self.inputs["rules"][0]
        rules=[base,replace(base,id="other",code="OTHER",org_id="foreign"),
               replace(base,id="pending",code="PENDING",status="pending"),
               replace(base,id="instagram",code="IG",scope=replace(base.scope,channel=("instagram",)))]
        p=Provider(); self.run_service(p,rules=rules)
        self.assertEqual([r["code"] for r in p.calls[0]["data"]["rules"]],["TONE-INV-03"])

    def test_only_selected_product_approved_facts_sent(self):
        p=Provider(); self.run_service(p)
        facts=p.calls[0]["data"]["facts"]
        self.assertEqual(len(facts),3)
        self.assertTrue(all(f["product"]=="Veyra Beat 200" for f in facts))
        self.assertTrue(any("999" in f["value"] for f in facts))

    def test_private_email_and_phone_redacted_before_provider(self):
        p=Provider()
        self.run_service(p,text="Contact demo@example.com or +91 98765 43210. Veyra Beat 200 ₹799.")
        payload=json.dumps(p.calls[0])
        self.assertNotIn("demo@example.com",payload)
        self.assertNotIn("98765",payload)
        self.assertIn("₹799",p.calls[0]["data"]["draft"])
        self.assertTrue(p.calls[0]["redacted"])

    def test_fabricated_quote_discarded(self):
        r=self.run_service(Provider({"findings":[tone("invented")]}))
        self.assertEqual(len(r.findings),1)
        self.assertEqual(r.ai_status,"validated_with_issues")

    def test_redacted_quote_cannot_create_wrong_original_span(self):
        r=self.run_service(Provider({"findings":[tone("[REDACTED_EMAIL]")]}),text="demo@example.com Veyra Beat 200 ₹799.")
        self.assertTrue(all(f.origin=="deterministic" for f in r.findings))

    def test_exception_or_malformed_root_preserves_checks_without_error_leak(self):
        for provider in [Provider(error=RuntimeError("fake-secret-key")),Provider(response={"approved":True})]:
            r=self.run_service(provider)
            self.assertEqual((r.ai_used,r.ai_status),(False,"unavailable"))
            self.assertEqual(len(r.findings),1)
            self.assertNotIn("fake-secret-key",str(r))

    def test_input_budget_does_not_truncate_or_call_provider(self):
        p=Provider(); r=self.run_service(p,text="x"*30001)
        self.assertEqual(r.ai_status,"input_limit")
        self.assertEqual(p.calls,[])

    def test_provider_scope_must_match_review(self):
        p=Provider(); p.org_id="foreign"
        with self.assertRaises(ValueError): self.run_service(p)

    def test_cache_reuse_and_deep_copy(self):
        p=Provider(); cache=ReviewCache()
        self.assertFalse(self.run_service(p,cache).cached)
        self.assertTrue(self.run_service(p,cache).cached)
        self.assertEqual(len(p.calls),1)
        cache.put("key",{"findings":[]}); r=cache.get("key");r["findings"].append("mutated")
        self.assertEqual(cache.get("key"),{"findings":[]})

    def test_cache_invalidated_by_text_context_rule_fact_version_and_model(self):
        changes=[dict(text=self.inputs["text"]+" More."),
            dict(context=replace(self.inputs["context"],audience="consumer")),
            dict(rules=[replace(self.inputs["rules"][0],version=2)]),
            dict(numeric_facts=[replace(f,version=2) for f in self.inputs["numeric_facts"]])]
        for change in changes:
            p=Provider(); cache=ReviewCache();self.run_service(p,cache)
            self.assertFalse(self.run_service(p,cache,**change).cached)
            self.assertEqual(len(p.calls),2)
        p=Provider();cache=ReviewCache();self.run_service(p,cache)
        p.cache_namespace="new-model";self.assertFalse(self.run_service(p,cache).cached)

    def test_cache_has_ttl_and_entry_bound(self):
        cache=ReviewCache(max_entries=1,ttl_seconds=1)
        cache.put("a",{"findings":[]});cache.put("b",{"findings":[]})
        self.assertIsNone(cache.get("a"))
        with patch("app.services.ai_review.time.monotonic",return_value=10**20): self.assertIsNone(cache.get("b"))

    def test_failed_and_rejected_output_not_cached(self):
        for p in [Provider(error=RuntimeError("failed")),Provider({"findings":[tone("invented")]})]:
            cache=ReviewCache();self.run_service(p,cache);self.run_service(p,cache)
            self.assertEqual(len(p.calls),2)

    def test_cache_without_provider_namespace_is_disabled(self):
        p=Provider();p.cache_namespace=None;cache=ReviewCache()
        self.run_service(p,cache);self.run_service(p,cache)
        self.assertEqual(len(p.calls),2)

    def test_no_key_real_adapter_gracefully_falls_back(self):
        with patch.dict(os.environ,{},clear=True):
            adapter=GeminiContentGenerator(org_id="demo-org",brand_id="veyra")
            r=self.run_service(adapter)
        self.assertFalse(r.ai_used)
        self.assertEqual(r.ai_status,"unavailable")

    def test_real_adapter_call_shape_using_test_fake_sdk_only(self):
        calls=[]
        class Client:
            def __init__(self,**kwargs):self.models=self
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def generate_content(self,**kwargs):
                calls.append(kwargs);return SimpleNamespace(text=json.dumps({"findings":[tone()]}))
        google=ModuleType("google");google.genai=SimpleNamespace(Client=Client)
        with patch.dict(sys.modules,{"google":google}),patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret","GEMINI_MODEL":"test-model"}):
            adapter=GeminiContentGenerator(org_id="demo-org",brand_id="veyra")
            r=self.run_service(adapter)
        self.assertTrue(r.ai_used)
        self.assertIn("response_json_schema",calls[0]["config"])
        self.assertNotIn("test-secret",str(adapter.events))
        self.assertEqual(adapter.events[0]["purpose"],"content_review")

    def test_provider_does_not_see_unapproved_fact(self):
        p=Provider();facts=[replace(f,status="pending") for f in self.inputs["numeric_facts"]]
        self.run_service(p,numeric_facts=facts)
        self.assertEqual(p.calls[0]["data"]["facts"],[])

    def test_low_confidence_ai_has_no_fix(self):
        item=tone();item["confidence"]=0.4
        r=self.run_service(Provider({"findings":[item]}))
        self.assertEqual((r.findings[-1].verdict,r.findings[-1].suggested_fix),("needs_review",None))


if __name__=="__main__":unittest.main()
