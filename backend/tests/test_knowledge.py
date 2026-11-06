from dataclasses import replace
import copy
import json
import os
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from app.services.extraction import extract_document
from app.services.knowledge_extract import extract_candidates, validate_candidates, _offline, RESPONSE_SCHEMA
from app.services.llm import GeminiKnowledgeGenerator, redact


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.doc = extract_document("demo.txt", (
            "Avoid cheap; use affordable.\nPaid ads must include T&C apply.\n"
            "Veyra Beat 200: price INR 999.\nVeyra Beat 200: battery life up to 40 hours.\n"
            "Veyra Beat 200: warranty 1 year.").encode())
        self.kw = dict(org_id="org", brand_id="brand", document_id="doc")

    def validate(self, data):
        return validate_candidates(self.doc, data, **self.kw, method="ai")

    def test_local_extraction_five_real_pending_candidates(self):
        r = extract_candidates(self.doc, **self.kw)
        self.assertEqual((r.method, len(r.candidates)), ("deterministic", 5))
        self.assertEqual([c.kind for c in r.candidates], ["rule", "rule", "fact", "fact", "fact"])
        self.assertTrue(all(c.status == "pending" for c in r.candidates))
        self.assertTrue(all(c.payload["market"] == "" for c in r.candidates))

    def test_sources_and_offsets_are_from_original_document(self):
        for c in extract_candidates(self.doc, **self.kw).candidates:
            self.assertEqual(self.doc.text[c.source_start:c.source_end], c.source.excerpt)
            self.assertEqual(c.source.document_id, "doc")
            self.assertTrue(c.source.location.startswith("line "))

    def test_fake_quote_dropped(self):
        data = _offline(self.doc); data["candidates"][0]["source_excerpt"] = "Fabricated rule."
        r = self.validate(data)
        self.assertEqual(len(r.candidates), 4)
        self.assertIn("absent", r.issues[0])

    def test_fake_block_dropped(self):
        for bad in [-1, True, 999]:
            data = _offline(self.doc); data["candidates"][0]["block_index"] = bad
            self.assertEqual(len(self.validate(data).candidates), 4)

    def test_model_cannot_supply_approval_or_org_fields(self):
        for field in ["status", "org_id", "page"]:
            data = _offline(self.doc); data["candidates"][0][field] = "approved"
            self.assertEqual(len(self.validate(data).candidates), 4)

    def test_wrong_value_and_nonfinite_numbers_dropped(self):
        for value in ["799", "NaN", "Infinity", "-1", "bad"]:
            data = _offline(self.doc); data["candidates"][2]["payload"]["value"] = value
            self.assertEqual(len(self.validate(data).candidates), 4)

    def test_invented_product_and_unit_dropped(self):
        for field, value in [("product", "Invented"), ("unit", "years")]:
            data = _offline(self.doc); data["candidates"][2]["payload"][field] = value
            self.assertEqual(len(self.validate(data).candidates), 4)

    def test_qualifier_cannot_be_removed(self):
        data = _offline(self.doc); data["candidates"][3]["payload"]["qualifier"] = "exact"
        self.assertEqual(len(self.validate(data).candidates), 4)

    def test_invented_preferred_term_dropped(self):
        data = _offline(self.doc); data["candidates"][0]["payload"]["preferred_term"] = "budget"
        self.assertEqual(len(self.validate(data).candidates), 4)

    def test_duplicate_candidates_deduplicated(self):
        data = _offline(self.doc); data["candidates"].append(copy.deepcopy(data["candidates"][0]))
        self.assertEqual(len(self.validate(data).candidates), 5)

    def test_stable_ids_include_tenant_and_document_version(self):
        a = extract_candidates(self.doc, **self.kw).candidates[0]
        self.assertEqual(a.id, extract_candidates(self.doc, **self.kw).candidates[0].id)
        b = extract_candidates(self.doc, org_id="other", brand_id="brand", document_id="doc").candidates[0]
        self.assertNotEqual(a.id, b.id)

    def test_unsupported_wording_is_not_faked(self):
        doc = extract_document("vague.txt", b"The brand feels lovely and inspiring.")
        r = extract_candidates(doc, **self.kw)
        self.assertEqual(r.candidates, ())
        self.assertTrue(any("limited explicit patterns" in issue for issue in r.issues))

    def test_provider_failure_falls_back_honestly(self):
        def fail(doc): raise RuntimeError("provider down")
        r = extract_candidates(self.doc, **self.kw, generator=fail)
        self.assertEqual((r.method, len(r.candidates)), ("deterministic_fallback", 5))

    def test_successful_provider_is_validated_not_trusted(self):
        data = _offline(self.doc); data["candidates"][0]["source_excerpt"] = "invented"
        r = extract_candidates(self.doc, **self.kw, generator=lambda doc: data)
        self.assertEqual((r.method, len(r.candidates)), ("ai", 4))

    def test_invalid_root_falls_back(self):
        r = extract_candidates(self.doc, **self.kw, generator=lambda doc: {"approved": True})
        self.assertEqual(r.method, "deterministic_fallback")

    def test_missing_scope_identifiers_rejected_before_provider(self):
        def fail(doc): self.fail("Must not send before validating scope")
        with self.assertRaises(ValueError):
            extract_candidates(self.doc, org_id="", brand_id="b", document_id="d", generator=fail)

    def test_source_markers_inside_document_do_not_change_citation(self):
        doc = extract_document("fake.txt", b"[[PAGE 999]]\nAvoid cheap; use affordable.")
        c = extract_candidates(doc, **self.kw).candidates[0]
        self.assertEqual(c.source.location, "line 2")

    def test_no_credentials_is_clear_and_no_network(self):
        with patch.dict(os.environ, {}, clear=True):
            r = extract_candidates(self.doc, **self.kw, generator=GeminiKnowledgeGenerator(org_id="org", brand_id="brand"))
            self.assertEqual(r.method, "deterministic_fallback")

    def test_redaction_preserves_prices_and_dates(self):
        output = redact("Email demo@example.com; phone +91 98765 43210. Price ₹999; date 2026-10-01")
        self.assertNotIn("demo@example.com", output)
        self.assertNotIn("98765", output)
        self.assertIn("₹999", output)
        self.assertIn("2026-10-01", output)

    def test_real_adapter_call_shape_with_fake_provider_boundary(self):
        calls = []
        class Client:
            def __init__(self, **kwargs): self.models = self
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def generate_content(self, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(text=json.dumps({"candidates": []}))
        google = ModuleType("google"); google.genai = SimpleNamespace(Client=Client)
        with patch.dict(sys.modules, {"google": google}), patch.dict(os.environ,
            {"GEMINI_API_KEY": "fictional-test-key", "GEMINI_MODEL": "test-model"}):
            adapter = GeminiKnowledgeGenerator(org_id="org", brand_id="brand")
            self.assertEqual(adapter(self.doc), {"candidates": []})
        self.assertIn("response_json_schema", calls[0]["config"])
        schema=calls[0]['config']['response_json_schema']
        self.assertNotIn('maxItems',schema['properties']['candidates'])
        self.assertEqual(RESPONSE_SCHEMA['properties']['candidates']['maxItems'],100)
        self.assertEqual(schema['properties']['candidates']['items'],RESPONSE_SCHEMA['properties']['candidates']['items'])
        self.assertTrue(adapter.events[0]["success"])
        self.assertNotIn("fictional-test-key", str(adapter.events))

    def test_provider_cannot_bypass_local_candidate_limit(self):
        excessive={'candidates':[_offline(self.doc)['candidates'][0]]*101}
        with self.assertRaisesRegex(ValueError,'At most 100'):
            self.validate(excessive)
        result=extract_candidates(self.doc,**self.kw,generator=lambda doc: excessive)
        self.assertEqual((result.method,len(result.candidates)),('deterministic_fallback',5))


if __name__ == "__main__": unittest.main()
