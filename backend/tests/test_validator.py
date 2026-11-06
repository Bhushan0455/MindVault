from dataclasses import replace
from datetime import date
import unittest

from app.services.contracts import Finding, ReviewContext, Rule, RuleScope, Source
from app.services.validator import ReviewEvidence, validate_ai_findings
from examples.validator_demo import proposed


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.text = "🎧 Hello! We are the best."
        self.context = ReviewContext("Veyra Beat 200", "IN", date(2026, 11, 5), channel="investor_deck")
        self.source = Source("guide", "Fictional Guide", "paragraph 3", "No exclamation marks.")
        self.rule = Rule("tone", "org", "brand", "TONE-INV-03", 1, "No exclamation marks", self.source,
                         status="approved", scope=RuleScope(channel=("investor_deck",)))
        self.fact = ReviewEvidence("fact", "org", "brand", 2, "Veyra Beat 200", "IN", self.source, status="approved")

    def validate(self, *items, text=None, rules=None, facts=None, deterministic=()):
        return validate_ai_findings(self.text if text is None else text, {"findings": list(items)},
            context=self.context, rules=[self.rule] if rules is None else rules,
            facts=[self.fact] if facts is None else facts, org_id="org", brand_id="brand", deterministic=deterministic)

    def test_valid_quote_rehydrates_rule_and_source(self):
        f = self.validate(proposed("Hello!")).findings[0]
        self.assertEqual(self.text[f.span_start:f.span_end], "Hello!")
        self.assertEqual((f.rule_id, f.rule_version, f.source), ("tone", 1, self.source))
        self.assertEqual(f.origin, "ai")

    def test_invented_quote_dropped(self):
        self.assertEqual(self.validate(proposed("invented")).findings, ())

    def test_unknown_rule_with_no_other_citation_dropped(self):
        self.assertEqual(self.validate(proposed("Hello!", rule_code="FAKE")).findings, ())

    def test_invalid_rule_removed_but_valid_fact_survives(self):
        f = self.validate(proposed("Hello!", rule_code="FAKE", fact_id="fact")).findings[0]
        self.assertIsNone(f.rule_code)
        self.assertEqual((f.fact_id, f.fact_version), ("fact", 2))

    def test_invalid_fact_removed_but_valid_rule_survives(self):
        f = self.validate(proposed("Hello!", fact_id="FAKE")).findings[0]
        self.assertIsNone(f.fact_id)
        self.assertEqual(f.rule_code, self.rule.code)

    def test_pending_expired_wrong_scope_foreign_rules_dropped(self):
        rules = [replace(self.rule, status="pending"), replace(self.rule, effective_to=date(2026, 1, 1)),
                 replace(self.rule, scope=RuleScope(channel=("instagram",))), replace(self.rule, org_id="other")]
        for rule in rules:
            self.assertEqual(self.validate(proposed("Hello!"), rules=[rule]).findings, ())

    def test_unapproved_foreign_wrong_product_market_and_expired_facts_dropped(self):
        invalid = [replace(self.fact, status="pending"), replace(self.fact, org_id="other"),
                   replace(self.fact, brand_id="other"), replace(self.fact, product="Other"),
                   replace(self.fact, market="US"), replace(self.fact, valid_to=date(2026, 1, 1)),
                   replace(self.fact, valid_from=date(2027, 1, 1))]
        for fact in invalid:
            self.assertEqual(self.validate(proposed("Hello!", rule_code=None, fact_id="fact"), facts=[fact]).findings, ())

    def test_low_confidence_downgraded_without_changing_severity(self):
        f = self.validate(proposed("Hello!", confidence=0.59, severity="critical")).findings[0]
        self.assertEqual((f.verdict, f.severity, f.suggested_fix), ("needs_review", "critical", None))

    def test_confidence_threshold_inclusive(self):
        self.assertEqual(self.validate(proposed("Hello!", confidence=0.6)).findings[0].verdict, "violation")

    def test_nan_boolean_out_of_range_confidence_rejected(self):
        for value in [float("nan"), float("inf"), True, -0.1, 1.1, "0.9"]:
            self.assertEqual(self.validate(proposed("Hello!", confidence=value)).findings, ())

    def test_whitespace_normalisation_maps_back_to_original(self):
        text = "🎧 Hello\n  there!"
        f = self.validate(proposed("Hello there!"), text=text).findings[0]
        self.assertEqual((f.quoted_text, text[f.span_start:f.span_end]), ("Hello\n  there!", "Hello\n  there!"))

    def test_repeated_quote_is_ambiguous_without_offsets(self):
        self.assertEqual(self.validate(proposed("Hello"), text="Hello and Hello").findings, ())
        self.assertEqual(self.validate(proposed("aaa"), text="aaaa").findings, ())

    def test_verified_offsets_resolve_repeated_quote(self):
        f = self.validate(proposed("Hello", span_start=10, span_end=15), text="Hello and Hello").findings[0]
        self.assertEqual(f.span_start, 10)

    def test_wrong_or_partial_offsets_rejected(self):
        for changes in [dict(span_start=0,span_end=1), dict(span_start=True,span_end=8), dict(span_start=2)]:
            self.assertEqual(self.validate(proposed("Hello!", **changes)).findings, ())

    def test_blank_quote_for_fake_missing_text_rejected(self):
        self.assertEqual(self.validate(proposed("")).findings, ())

    def test_ai_cannot_supply_source_or_approval_fields(self):
        for key in ["source", "status", "rule_version", "approved_by"]:
            self.assertEqual(self.validate(proposed("Hello!", **{key:"invented"})).findings, ())

    def test_false_verdict_dropped_and_truth_judgement_downgraded(self):
        self.assertEqual(self.validate(proposed("best", verdict="false")).findings, ())
        f = self.validate(proposed("best", explanation="This claim is false.")).findings[0]
        self.assertEqual(f.verdict, "needs_review")
        self.assertNotIn("false", f.explanation)

    def test_supported_without_fact_requires_review(self):
        f = self.validate(proposed("best", verdict="supported", severity="info")).findings[0]
        self.assertEqual((f.verdict, f.severity), ("needs_review", "high"))

    def test_supported_fact_retains_dependency_and_no_fix(self):
        f = self.validate(proposed("best", verdict="supported", fact_id="fact")).findings[0]
        self.assertEqual((f.verdict, f.severity, f.fact_id, f.suggested_fix), ("supported", "info", "fact", None))

    def deterministic(self, category="tone"):
        return Finding("deterministic", category, "high", 1.0, "violation", 2, 8, "Hello!", "Known check", "Hello", None, None, self.source)

    def test_deterministic_result_wins_over_same_category_overlap(self):
        d = self.deterministic()
        r = self.validate(proposed("Hello!"), deterministic=(d,))
        self.assertEqual(r.findings, (d,))

    def test_distinct_category_overlap_preserved(self):
        self.assertEqual(len(self.validate(proposed("Hello!"), deterministic=(self.deterministic("price"),)).findings),2)

    def test_stale_deterministic_offsets_fail_explicitly(self):
        with self.assertRaises(ValueError): self.validate(proposed("best"), deterministic=(replace(self.deterministic(), quoted_text="Wrong"),))

    def test_duplicates_merged_and_conflicting_suggestions_require_review(self):
        self.assertEqual(len(self.validate(proposed("Hello!"), proposed("Hello!")).findings),1)
        f = self.validate(proposed("Hello!"), proposed("Hello!", suggested_fix="Greetings")).findings[0]
        self.assertEqual((f.verdict, f.suggested_fix), ("needs_review", None))

    def test_nonoverlapping_and_distinct_rule_findings_preserved(self):
        self.assertEqual(len(self.validate(proposed("Hello!"), proposed("best")).findings),2)
        other = replace(self.rule, id="other",code="OTHER")
        r = self.validate(proposed("Hello!"), proposed("Hello!", rule_code="OTHER"), rules=[self.rule,other])
        self.assertEqual(len(r.findings),2)

    def test_duplicate_rule_versions_and_fact_ids_fail_explicitly(self):
        with self.assertRaises(ValueError): self.validate(proposed("Hello!"),rules=[self.rule, replace(self.rule,version=2)])
        with self.assertRaises(ValueError): self.validate(proposed("Hello!"),facts=[self.fact,self.fact])

    def test_invalid_root_rejected(self):
        for response in [[], {"findings":None}, {"findings":[],"approved":True}]:
            with self.assertRaises(ValueError):
                validate_ai_findings(self.text,response,context=self.context,rules=[],facts=[],org_id="org",brand_id="brand")


if __name__ == "__main__": unittest.main()
