from dataclasses import replace
import unittest

from app.services.contracts import Finding
from app.services.fixes import FixDecision, FixError, apply_selected_fixes, body_hash


class FixTests(unittest.TestCase):
    def setUp(self):
        self.text = "🎧 Price ₹799. A cheap deal."

    def decision(self, quote, replacement, status="accepted", id="f1", **kwargs):
        start = self.text.index(quote)
        finding = Finding("deterministic", "terminology", "high", 1.0, "violation", start, start+len(quote),
                          quote, "Fictional explanation", replacement, None, None, None)
        return FixDecision(id, "r1", finding, status, **kwargs)

    def apply(self, decisions, text=None, hash=None):
        return apply_selected_fixes(self.text if text is None else text, revision_id="r1",
                                   expected_body_hash=body_hash(self.text) if hash is None else hash, decisions=decisions)

    def error(self, code, decisions, **kwargs):
        with self.assertRaises(FixError) as raised: self.apply(decisions, **kwargs)
        self.assertEqual(raised.exception.code, code)

    def insertion(self, position, replacement, id="insert"):
        d = self.decision("cheap", replacement, id=id)
        return replace(d, finding=replace(d.finding, span_start=position, span_end=position, quoted_text=""))

    def test_multiple_length_changing_fixes_keep_original_offsets(self):
        result = self.apply([self.decision("₹799", "₹999", id="price"), self.decision("cheap", "affordable", id="term")])
        self.assertEqual(result.body_text, "🎧 Price ₹999. A affordable deal.")
        self.assertEqual(len(result.applied), 2)
        self.assertEqual(result.body_hash, body_hash(result.body_text))

    def test_input_decision_order_does_not_change_output(self):
        ds = [self.decision("₹799", "₹999", id="price"), self.decision("cheap", "affordable", id="term")]
        self.assertEqual(self.apply(ds), self.apply(list(reversed(ds))))

    def test_edited_replacement_takes_priority_over_suggestion(self):
        r = self.apply([self.decision("cheap", "affordable", status="edited", edited_text="budget-friendly")])
        self.assertIn("budget-friendly", r.body_text)
        self.assertNotIn("affordable", r.body_text)

    def test_explicit_empty_edit_deletes_span(self):
        r = self.apply([self.decision("cheap ", "affordable ", status="edited", edited_text="")])
        self.assertEqual(r.body_text, "🎧 Price ₹799. A deal.")

    def test_rejected_open_dismissed_not_applied(self):
        for status in ["rejected", "open", "dismissed"]:
            r = self.apply([self.decision("cheap", "affordable", status=status, note="Fictional review reason")])
            self.assertFalse(r.changed)
            self.assertEqual(r.body_text, self.text)
            self.assertEqual(len(r.skipped), 1)

    def test_rejection_requires_reason(self):
        self.error("missing_reason", [self.decision("cheap", "affordable", status="rejected")])

    def test_unavailable_suggestion_needs_explicit_human_edit(self):
        self.error("fix_unavailable", [self.decision("cheap", None)])
        self.assertTrue(self.apply([self.decision("cheap", None, status="edited", edited_text="affordable")]).changed)

    def test_edited_requires_replacement(self):
        self.error("fix_unavailable", [self.decision("cheap", "affordable", status="edited")])

    def test_stale_text_hash_detects_changes_outside_quoted_span(self):
        self.error("stale_text", [self.decision("cheap", "affordable")], text=self.text+" New text.")

    def test_foreign_revision_rejected_even_if_text_matches(self):
        self.error("stale_revision", [replace(self.decision("cheap", "affordable"), revision_id="r0")])

    def test_stale_quote_at_saved_offsets_rejected(self):
        d = self.decision("cheap", "affordable")
        self.error("stale_span", [replace(d, finding=replace(d.finding, quoted_text="other"))])

    def test_invalid_and_boolean_offsets_rejected(self):
        for start,end in [(-1,2), (0,999), (5,4), (True,2)]:
            d = self.decision("cheap", "affordable")
            self.error("invalid_span", [replace(d, finding=replace(d.finding,span_start=start,span_end=end))])

    def test_emoji_positions_use_python_codepoints(self):
        r = self.apply([self.decision("🎧", "Headphones")])
        self.assertTrue(r.body_text.startswith("Headphones Price"))

    def test_end_insertion_and_separate_replacement(self):
        r = self.apply([self.decision("cheap", "affordable"), self.insertion(len(self.text), "\nT&C apply")])
        self.assertEqual(r.body_text, "🎧 Price ₹799. A affordable deal.\nT&C apply")

    def test_empty_draft_insertion(self):
        self.text=""
        f = Finding("deterministic", "disclaimer", "high", 1.0, "violation",0,0,"","Missing text","T&C apply",None,None,None)
        r = self.apply([FixDecision("f1","r1",f,"accepted")])
        self.assertEqual(r.body_text,"T&C apply")

    def test_two_insertions_at_same_position_conflict(self):
        self.error("insertion_conflict", [self.insertion(len(self.text),"A",id="a"),self.insertion(len(self.text),"B",id="b")])

    def test_insertion_inside_or_at_replacement_boundaries_conflicts(self):
        d = self.decision("cheap", "affordable")
        for position in [d.finding.span_start, d.finding.span_start+1, d.finding.span_end]:
            self.error("insertion_conflict", [d,self.insertion(position,"extra")])

    def test_overlapping_replacements_reject_whole_batch(self):
        self.error("overlapping_fixes", [self.decision("cheap", "affordable", id="term"),
                                          self.decision("cheap deal", "offer", id="phrase")])
        self.assertEqual(self.text, "🎧 Price ₹799. A cheap deal.")

    def test_adjacent_nonempty_replacements_allowed(self):
        r = self.apply([self.decision("cheap", "great", id="a"), self.decision(" deal", " offer", id="b")])
        self.assertTrue(r.body_text.endswith("great offer."))

    def test_duplicate_finding_id_rejected(self):
        d = self.decision("cheap","affordable")
        self.error("duplicate_finding", [d,d])

    def test_noop_and_no_decisions_return_unchanged(self):
        self.assertFalse(self.apply([]).changed)
        r = self.apply([self.decision("cheap","cheap")])
        self.assertFalse(r.changed)
        self.assertEqual(r.applied, ())
        self.assertEqual(len(r.skipped),1)

    def test_supported_result_not_treated_as_correction(self):
        d = self.decision("₹799","₹999")
        self.error("supported_finding",[replace(d,finding=replace(d.finding,verdict="supported"))])

    def test_unknown_status_rejected(self):
        self.error("invalid_decision",[self.decision("cheap","affordable",status="auto")])

    def test_malformed_hash_fails_safely(self):
        self.error("stale_text", [], hash="é"*64)

    def test_size_limit_checked_before_constructing_large_result(self):
        self.error("text_limit", [self.decision("cheap", "x"*1_000_001)])


if __name__ == "__main__": unittest.main()
