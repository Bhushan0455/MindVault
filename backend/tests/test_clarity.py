from dataclasses import FrozenInstanceError, replace
import unittest

from app.services.clarity import audit_clarity, proposal_is_current
from app.services.contracts import Rule, RuleScope, Source


class ClarityTests(unittest.TestCase):
    def setUp(self):
        self.rule=Rule("r1","org","brand","HEADLINE-01",1,"Headlines should be short.",
            Source("guide","Fictional Guide","paragraph 1","Headlines should be short."),status="pending")

    def audit(self,*rules):
        return audit_clarity(list(rules or (self.rule,)),org_id="org",brand_id="brand")

    def test_missing_headline_threshold_has_explanation_and_examples(self):
        f=self.audit().findings[0]
        self.assertEqual((f.kind,f.status,f.method),("missing_threshold","pending","deterministic"))
        self.assertIn("8 words",f.suggested_rewrite)
        self.assertTrue(f.why_it_matters and f.example_good and f.example_bad)
        self.assertTrue(any("not in the source" in a for a in f.assumptions))

    def test_threshold_examples_obey_proposed_limit(self):
        f=self.audit().findings[0]
        self.assertLessEqual(len(f.example_good.split()),8)
        self.assertGreater(len(f.example_bad.split()),8)

    def test_explicit_threshold_not_flagged(self):
        for instruction in ["Headlines should be short, at most 8 words.","Headlines should be short: eight words maximum.",
                            "Headlines must contain no more than 8 words."]:
            self.assertEqual(self.audit(replace(self.rule,instruction=instruction)).findings,())

    def test_unrelated_number_does_not_supply_length_limit(self):
        self.assertEqual(len(self.audit(replace(self.rule,instruction="For campaign 2026 headlines should be short.")).findings),1)

    def test_threshold_in_other_sentence_does_not_hide_problem(self):
        r=replace(self.rule,instruction="Use 2 images. Headlines should be short.")
        self.assertEqual(len(self.audit(r).findings),1)

    def test_valid_brand_principles_not_called_invalid(self):
        for instruction in ["Be approachable.","Use a friendly tone.","Keep the brand professional."]:
            self.assertEqual(self.audit(replace(self.rule,instruction=instruction)).findings,())

    def test_negative_rules_not_reversed_by_positive_rewrite(self):
        for instruction in ["Headlines must not be short.","Never use attractive visuals."]:
            self.assertEqual(self.audit(replace(self.rule,instruction=instruction)).findings,())

    def test_visual_criteria_needs_admin_completion(self):
        f=self.audit(replace(self.rule,instruction="Use attractive visuals.")).findings[0]
        self.assertEqual(f.kind,"undefined_term")
        self.assertTrue(f.requires_completion)
        self.assertIn("[colour palette]",f.suggested_rewrite)
        self.assertTrue(any("no visual was inspected" in a for a in f.assumptions))

    def test_measurable_visual_instruction_not_flagged(self):
        self.assertEqual(self.audit(replace(self.rule,instruction="Use the approved blue palette and place the logo at top left.")).findings,())

    def test_conditional_scope_gap(self):
        f=self.audit(replace(self.rule,instruction="Include the disclaimer where appropriate.")).findings[0]
        self.assertEqual(f.kind,"scope_gap")
        self.assertTrue(f.requires_completion)
        self.assertIn("Include the disclaimer",f.suggested_rewrite)

    def test_structured_scope_avoids_unscoped_condition_warning(self):
        r=replace(self.rule,instruction="Include the disclaimer where appropriate.",scope=RuleScope(content_type=("paid_ad",)))
        self.assertEqual(self.audit(r).findings,())

    def test_other_sentences_preserved_in_proposed_rewrite(self):
        r=replace(self.rule,instruction="Use the brand name. Headlines should be short. Include T&C apply.")
        f=self.audit(r).findings[0]
        self.assertTrue(f.suggested_rewrite.startswith("Use the brand name. "))
        self.assertTrue(f.suggested_rewrite.endswith(" Include T&C apply."))
        self.assertEqual(r.instruction[f.span_start:f.span_end],f.excerpt)

    def test_unicode_offsets_slice_original_instruction(self):
        r=replace(self.rule,instruction="🎧 Brand notes.  Headlines should be short.")
        f=self.audit(r).findings[0]
        self.assertEqual(r.instruction[f.span_start:f.span_end],"Headlines should be short.")

    def test_foreign_org_and_brand_never_exposed(self):
        result=self.audit(replace(self.rule,org_id="other"),replace(self.rule,brand_id="other"))
        self.assertEqual((result.findings,result.checked_rule_ids), ((),()))

    def test_candidate_and_approved_rules_can_be_audited(self):
        for status in ["extracted","pending","approved"]:
            self.assertEqual(len(self.audit(replace(self.rule,status=status)).findings),1)
        for status in ["rejected","superseded"]:
            self.assertEqual(self.audit(replace(self.rule,status=status)).findings,())

    def test_source_is_preserved_not_fabricated(self):
        f=self.audit().findings[0]
        self.assertEqual(f.source,self.rule.source)
        self.assertEqual((f.rule_id,f.rule_code,f.rule_version),(self.rule.id,self.rule.code,1))

    def test_deterministic_id_and_stale_proposal_detection(self):
        f=self.audit().findings[0]
        self.assertEqual(f.id,self.audit().findings[0].id)
        self.assertTrue(proposal_is_current(self.rule,f))
        for changes in [dict(instruction="Headlines should be concise."),dict(version=2),
                        dict(scope=RuleScope(channel=("instagram",))),dict(status="approved"),dict(org_id="other")]:
            self.assertFalse(proposal_is_current(replace(self.rule,**changes),f))

    def test_audit_never_mutates_original_rule(self):
        self.audit()
        self.assertEqual(self.rule.instruction,"Headlines should be short.")
        self.assertEqual(self.rule.status,"pending")
        with self.assertRaises(FrozenInstanceError): self.audit().findings[0].status="approved"

    def test_different_length_subjects_get_suitable_proposals(self):
        for instruction, expected in [("Sentences should be concise.","20 words"),
            ("Paragraphs should be brief.","3 sentences"),("Copy should be concise.","60 words"),
            ("Captions should be short.","8 words")]:
            self.assertIn(expected,self.audit(replace(self.rule,instruction=instruction)).findings[0].suggested_rewrite)

    def test_duplicate_ids_and_blank_tenant_rejected(self):
        with self.assertRaises(ValueError): self.audit(self.rule,self.rule)
        with self.assertRaises(ValueError): audit_clarity([],org_id="",brand_id="brand")

    def test_no_findings_is_not_a_certificate_of_clarity(self):
        r=self.audit(replace(self.rule,instruction="Follow the documented terminology list."))
        self.assertEqual(r.findings,())
        self.assertTrue(any("does not prove clarity" in i for i in r.issues))


if __name__ == "__main__": unittest.main()
