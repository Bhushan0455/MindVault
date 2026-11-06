import unittest
from dataclasses import replace
from datetime import date

from app.services.contracts import ClaimEvidence, ReviewContext, Rule, RuleScope, Source
from app.services.rule_checks import check_rules


class RuleChecks(unittest.TestCase):
    def setUp(self):
        self.source = Source("guide", "Fictional Guide", "section 3", "Use affordable, not cheap.")
        self.context = ReviewContext("Veyra Beat 200", "IN", date(2026, 11, 5),
                                     channel="instagram", audience="consumer", content_type="paid_ad")
        self.term = Rule("term", "org", "brand", "TERM-01", 1, "Avoid cheap", self.source,
                         status="approved", severity="medium", forbidden_terms=("cheap",),
                         preferred_terms=(("cheap", "affordable"),))
        self.disclaimer = replace(self.term, id="disc", code="DISC-01", severity="high",
            forbidden_terms=(), preferred_terms=(), required_text="T&C apply",
            scope=RuleScope(content_type=("paid_ad",)))
        self.claim = replace(self.term, id="claim", code="CLAIM-01", severity="high",
            forbidden_terms=(), preferred_terms=(), requires_claim_evidence=True)
        self.evidence = ClaimEvidence("e1", "org", "brand", 1, "Veyra Beat 200", "IN",
            "Best headphones in India.", Source("evidence", "Fictional Claims Sheet", "paragraph 2",
                                                "Best headphones in India."), status="approved")

    def run_checks(self, text, rules=None, evidence=None, context=None):
        return check_rules(text, context or self.context,
                           [self.term, self.disclaimer, self.claim] if rules is None else rules,
                           evidence or [], org_id="org", brand_id="brand")

    def test_terminology_has_exact_span_replacement_and_rule_evidence(self):
        text = "🎧 A CHEAP deal"
        f = self.run_checks(text, [self.term]).findings[0]
        self.assertEqual(text[f.span_start:f.span_end], "CHEAP")
        self.assertEqual((f.suggested_fix, f.rule_code, f.rule_version), ("affordable", "TERM-01", 1))
        self.assertEqual(f.source, self.source)

    def test_forbidden_word_does_not_match_inside_other_words(self):
        self.assertEqual(self.run_checks("cheapest cheaply cheapness", [self.term]).findings, ())

    def test_repeated_terms_have_distinct_spans(self):
        fs = self.run_checks("cheap and cheap", [self.term]).findings
        self.assertEqual([f.span_start for f in fs], [0, 10])

    def test_preferred_mapping_alone_is_enforced(self):
        rule = replace(self.term, forbidden_terms=())
        self.assertEqual(self.run_checks("cheap", [rule]).findings[0].suggested_fix, "affordable")

    def test_term_without_replacement_does_not_invent_a_fix(self):
        rule = replace(self.term, preferred_terms=())
        self.assertIsNone(self.run_checks("cheap", [rule]).findings[0].suggested_fix)

    def test_longest_overlapping_term_wins_within_rule(self):
        rule = replace(self.term, forbidden_terms=("cheap", "cheap deal"), preferred_terms=())
        fs = self.run_checks("cheap deal", [rule]).findings
        self.assertEqual([f.quoted_text for f in fs], ["cheap deal"])

    def test_blank_terms_do_not_match_everywhere(self):
        rule = replace(self.term, forbidden_terms=("", " "), preferred_terms=())
        self.assertEqual(self.run_checks("text", [rule]).findings, ())

    def test_missing_disclaimer_inserts_at_end_without_changing_text(self):
        text = "Buy today!"
        f = self.run_checks(text, [self.disclaimer]).findings[0]
        self.assertEqual((f.span_start, f.span_end, f.quoted_text), (len(text), len(text), ""))
        self.assertEqual(text[:f.span_start] + f.suggested_fix + text[f.span_end:], "Buy today!\nT&C apply")

    def test_disclaimer_on_empty_draft(self):
        f = self.run_checks("", [self.disclaimer]).findings[0]
        self.assertEqual((f.span_start, f.suggested_fix), (0, "T&C apply"))

    def test_disclaimer_case_and_whitespace_normalised(self):
        self.assertEqual(self.run_checks("Offer. t&c\n APPLY.", [self.disclaimer]).findings, ())

    def test_disclaimer_substring_does_not_count(self):
        self.assertEqual(len(self.run_checks("T&C applying", [self.disclaimer]).findings), 1)

    def test_disclaimer_only_for_matching_content_type(self):
        result = self.run_checks("Buy now", [self.disclaimer], context=replace(self.context, content_type="blog"))
        self.assertEqual(result.findings, ())
        self.assertEqual(len(result.resolution.skipped), 1)

    def test_superlative_unsupported_not_false_and_no_automatic_fix(self):
        f = self.run_checks("Best headphones in India.", [self.claim]).findings[0]
        self.assertEqual((f.verdict, f.severity, f.rule_code), ("unsupported", "high", "CLAIM-01"))
        self.assertIn("not substantiated", f.explanation)
        self.assertIsNone(f.suggested_fix)
        self.assertIsNone(f.fact_id)

    def test_all_lexicon_markers_detected_without_word_substrings(self):
        for phrase in ["best", "#1", "number one", "leading", "cheapest", "fastest", "guaranteed",
                       "100%", "only", "unbeatable", "better than"]:
            with self.subTest(phrase=phrase):
                self.assertEqual(len(self.run_checks(phrase, [self.claim]).findings), 1)
        self.assertEqual(self.run_checks("bestow fastestever lonely", [self.claim]).findings, ())

    def test_exact_approved_claim_records_dependency(self):
        f = self.run_checks("Best headphones in India!", [self.claim], [self.evidence]).findings[0]
        self.assertEqual((f.verdict, f.severity, f.fact_id, f.fact_version), ("supported", "info", "e1", 1))
        self.assertEqual(f.source.document_title, "Fictional Claims Sheet")

    def test_unrelated_claim_evidence_cannot_support_superlative(self):
        evidence = replace(self.evidence, claim_text="Battery life up to 40 hours.")
        self.assertEqual(self.run_checks("Best headphones in India.", [self.claim], [evidence]).findings[0].verdict,
                         "unsupported")

    def test_claim_evidence_must_match_org_brand_product_market_status_dates(self):
        invalid = [replace(self.evidence, org_id="other"), replace(self.evidence, brand_id="other"),
                   replace(self.evidence, product="Other"), replace(self.evidence, market="US"),
                   replace(self.evidence, status="pending"), replace(self.evidence, status="rejected"),
                   replace(self.evidence, valid_from=date(2027, 1, 1)),
                   replace(self.evidence, valid_to=date(2026, 1, 1))]
        for evidence in invalid:
            with self.subTest(evidence=evidence):
                self.assertEqual(self.run_checks("Best headphones in India.", [self.claim], [evidence])
                                 .findings[0].verdict, "unsupported")

    def test_claim_evidence_inclusive_dates(self):
        evidence = replace(self.evidence, valid_from=self.context.publication_date,
                           valid_to=self.context.publication_date)
        self.assertEqual(self.run_checks("Best headphones in India.", [self.claim], [evidence])
                         .findings[0].verdict, "supported")

    def test_evidence_for_one_sentence_does_not_cover_another(self):
        text = "Best headphones in India. Guaranteed happiness!"
        fs = self.run_checks(text, [self.claim], [self.evidence]).findings
        self.assertEqual([f.verdict for f in fs], ["supported", "unsupported"])

    def test_unapproved_and_foreign_rules_never_produce_findings(self):
        rules = [replace(self.term, status="pending"), replace(self.claim, org_id="other"),
                 replace(self.disclaimer, brand_id="other")]
        self.assertEqual(self.run_checks("Best cheap headphones", rules).findings, ())

    def test_no_claim_check_without_explicit_claim_rule(self):
        self.assertEqual(self.run_checks("Best headphones", []).findings, ())

    def test_combined_results_and_cleaner_draft(self):
        result = self.run_checks("Best cheap headphones!")
        self.assertEqual({f.category for f in result.findings}, {"claims", "terminology", "disclaimer"})
        self.assertEqual(self.run_checks("An affordable option. T&C apply").findings, ())


if __name__ == "__main__":
    unittest.main()
