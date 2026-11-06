from copy import deepcopy
from dataclasses import replace
import json
import os
import sys
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch

from app.services.ai_clarity import GeminiClarityGenerator,run_clarity_audit
from app.services.ai_review import ReviewCache
from app.services.clarity import rule_snapshot_hash,proposal_is_current
from examples.ai_clarity_demo import demo_rules


class Provider:
    """Test boundary fake, never used by production or the CLI demo."""
    model="test-model"
    cache_namespace="test-clarity-v1"
    def __init__(self,response=None,error=None):
        self.response={"clarity_findings":[]} if response is None else response
        self.error=error;self.calls=[]
    def __call__(self,payload):
        self.calls.append(deepcopy(payload))
        if self.error:raise self.error
        return deepcopy(self.response)


def proposal(rule,**changes):
    item=dict(rule_id=rule.id,rule_version=rule.version,rule_snapshot_hash=rule_snapshot_hash(rule),
        kind="undefined_term",excerpt=rule.instruction,why_it_matters="Reviewers lack concrete examples of business-friendly wording.",
        suggested_rewrite="Use plain explanations for the defined audience. Add [approved vocabulary] and one accepted example.",
        example_good="An explanation using admin-approved plain language.",example_bad="An explanation using unexplained specialist jargon.",confidence=0.9)
    item.update(changes);return item


class AIClarityTests(unittest.TestCase):
    def setUp(self):self.rules=demo_rules()
    def run_service(self,provider=None,cache=None,rules=None):
        return run_clarity_audit(self.rules if rules is None else rules,org_id="demo-org",brand_id="veyra",generator=provider,cache=cache)

    def test_without_provider_only_real_deterministic_finding(self):
        r=self.run_service()
        self.assertEqual((r.ai_used,r.ai_status,len(r.findings)),(False,"not_requested",1))
        self.assertEqual(r.findings[0].method,"deterministic")

    def test_valid_ai_proposal_pending_and_snapshot_bound(self):
        p=Provider({"clarity_findings":[proposal(self.rules[1])]})
        r=self.run_service(p);f=r.findings[-1]
        self.assertEqual((r.ai_used,f.method,f.status),(True,"ai","pending"))
        self.assertTrue(proposal_is_current(self.rules[1],f))
        self.assertTrue(f.requires_completion)
        self.assertEqual(f.source,self.rules[1].source)

    def test_fabricated_quote_dropped(self):
        r=self.run_service(Provider({"clarity_findings":[proposal(self.rules[1],excerpt="invented")]}))
        self.assertEqual((len(r.findings),r.ai_status),(1,"validated_with_issues"))

    def test_unknown_rule_stale_version_and_stale_hash_dropped(self):
        for changes in [dict(rule_id="unknown"),dict(rule_version=2),dict(rule_snapshot_hash="invented")]:
            r=self.run_service(Provider({"clarity_findings":[proposal(self.rules[1],**changes)]}))
            self.assertEqual(len(r.findings),1)

    def test_model_cannot_supply_source_or_approval(self):
        for key in ["source","status","approved_by","authority"]:
            r=self.run_service(Provider({"clarity_findings":[proposal(self.rules[1],**{key:"invented"})]}))
            self.assertEqual(len(r.findings),1)

    def test_low_nonfinite_boolean_confidence_dropped(self):
        for value in [0.59,float("nan"),float("inf"),True,-1,2]:
            r=self.run_service(Provider({"clarity_findings":[proposal(self.rules[1],confidence=value)]}))
            self.assertEqual(len(r.findings),1)

    def test_deterministic_priority_and_ai_duplicates(self):
        item=proposal(self.rules[0],kind="missing_threshold")
        r=self.run_service(Provider({"clarity_findings":[item]}))
        self.assertEqual(len(r.findings),1)
        self.assertEqual(r.findings[0].method,"deterministic")
        item=proposal(self.rules[1])
        r=self.run_service(Provider({"clarity_findings":[item,item]}))
        self.assertEqual(len(r.findings),2)
        self.assertTrue(any("Merged" in i for i in r.issues))

    def test_invented_numeric_limit_explicitly_labelled(self):
        item=proposal(self.rules[1],suggested_rewrite="Use no more than 12 technical terms and define every term.")
        f=self.run_service(Provider({"clarity_findings":[item]})).findings[-1]
        self.assertTrue(any("illustrative" in a for a in f.assumptions))

    def test_unchanged_rewrite_and_unsupported_contradiction_dropped(self):
        for changes in [dict(suggested_rewrite=self.rules[1].instruction),dict(kind="contradiction")]:
            r=self.run_service(Provider({"clarity_findings":[proposal(self.rules[1],**changes)]}))
            self.assertEqual(len(r.findings),1)

    def test_foreign_rejected_and_superseded_rules_not_sent(self):
        base=self.rules[1]
        rules=[*self.rules,replace(base,id="foreign",org_id="other"),
               replace(base,id="rejected",status="rejected"),replace(base,id="old",status="superseded")]
        p=Provider();self.run_service(p,rules=rules)
        self.assertEqual({r["rule_id"] for r in p.calls[0]["data"]["rules"]},{"headline","business"})

    def test_redaction_keeps_trusted_hash_and_removes_private_text(self):
        r=replace(self.rules[1],instruction="Ask demo@example.com for business-friendly wording.")
        p=Provider();self.run_service(p,rules=[r])
        payload=p.calls[0]
        self.assertNotIn("demo@example.com",json.dumps(payload))
        self.assertEqual(payload["data"]["rules"][0]["rule_snapshot_hash"],rule_snapshot_hash(r))
        self.assertTrue(payload["redacted"])

    def test_failure_and_bad_root_retain_deterministic_without_secret_leak(self):
        for p in [Provider(error=RuntimeError("private-test-secret")),Provider({"approved":True})]:
            r=self.run_service(p)
            self.assertEqual((r.ai_used,r.ai_status,len(r.findings)),(False,"unavailable",1))
            self.assertNotIn("private-test-secret",str(r))

    def test_no_eligible_rules_skips_provider(self):
        p=Provider();r=self.run_service(p,rules=[])
        self.assertEqual(r.ai_status,"no_rules")
        self.assertEqual(p.calls,[])

    def test_input_budget_prevents_provider_call(self):
        rules=[replace(self.rules[1],id=str(i),instruction="x"*16000) for i in range(3)]
        p=Provider();r=self.run_service(p,rules=rules)
        self.assertEqual(r.ai_status,"input_limit")
        self.assertEqual(p.calls,[])

    def test_adapter_tenant_mismatch_rejected(self):
        p=Provider();p.org_id="foreign"
        with self.assertRaises(ValueError):self.run_service(p)

    def test_cached_results_revalidated_and_snapshot_changes_invalidate(self):
        p=Provider();cache=ReviewCache()
        self.assertFalse(self.run_service(p,cache).cached)
        self.assertTrue(self.run_service(p,cache).cached)
        self.assertEqual(len(p.calls),1)
        self.assertFalse(self.run_service(p,cache,rules=[replace(r,version=2) for r in self.rules]).cached)
        self.assertEqual(len(p.calls),2)

    def test_failed_or_rejected_proposals_not_cached(self):
        for p in [Provider(error=RuntimeError("down")),Provider({"clarity_findings":[proposal(self.rules[1],excerpt="fake")]})]:
            cache=ReviewCache();self.run_service(p,cache);self.run_service(p,cache)
            self.assertEqual(len(p.calls),2)

    def test_missing_key_real_adapter_falls_back(self):
        with patch.dict(os.environ,{},clear=True):
            r=self.run_service(GeminiClarityGenerator(org_id="demo-org",brand_id="veyra"))
        self.assertEqual((r.ai_used,r.ai_status),(False,"unavailable"))

    def test_real_clarity_adapter_uses_own_schema_prompt_and_audit_purpose(self):
        calls=[]
        class Client:
            def __init__(self,**kwargs):self.models=self
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def generate_content(self,**kwargs):
                calls.append(kwargs);return SimpleNamespace(text=json.dumps({"clarity_findings":[]}))
        google=ModuleType("google");google.genai=SimpleNamespace(Client=Client)
        with patch.dict(sys.modules,{"google":google}),patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret","GEMINI_MODEL":"test-model"}):
            adapter=GeminiClarityGenerator(org_id="demo-org",brand_id="veyra")
            result=self.run_service(adapter)
        self.assertTrue(result.ai_used)
        self.assertIn("clarity_findings",calls[0]["config"]["response_json_schema"]["properties"])
        self.assertEqual(adapter.events[0]["purpose"],"clarity_audit")
        self.assertNotIn("test-secret",str(adapter.events))


if __name__=="__main__":unittest.main()
