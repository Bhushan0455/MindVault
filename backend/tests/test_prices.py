import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.services.checks import check_prices
from app.services.contracts import PriceFact, ReviewContext, Source


class PriceChecks(unittest.TestCase):
    def setUp(self):
        self.source = Source("doc-1", "Fictional Fact Sheet", "page 2", "India price: ₹999")
        self.fact = PriceFact("fact-1", 1, "Veyra Beat 200", "IN", Decimal("999"),
                              "INR", "approved", date(2026, 10, 1), self.source)
        self.context = ReviewContext("Veyra Beat 200", "IN", date(2026, 11, 5))

    def check(self, text, facts=None):
        return check_prices(text, self.context, [self.fact] if facts is None else facts)

    def test_wrong_price_has_evidence_and_exact_fix(self):
        text = "Headphones now at ₹799!"
        f = self.check(text)[0]
        self.assertEqual((f.verdict, f.severity, f.suggested_fix), ("violation", "critical", "₹999"))
        self.assertEqual(text[f.span_start:f.span_end], "₹799")
        self.assertEqual((f.fact_id, f.source.location), ("fact-1", "page 2"))
        self.assertEqual(text[:f.span_start] + f.suggested_fix + text[f.span_end:], "Headphones now at ₹999!")

    def test_matching_price_retains_fact_dependency(self):
        f = self.check("Price ₹999")[0]
        self.assertEqual((f.verdict, f.severity, f.fact_id), ("supported", "info", "fact-1"))
        self.assertIsNone(f.suggested_fix)

    def test_pending_rejected_and_future_facts_not_used(self):
        for fact in [replace(self.fact, status="pending"), replace(self.fact, status="rejected"),
                     replace(self.fact, valid_from=date(2027, 1, 1))]:
            with self.subTest(fact=fact):
                self.assertEqual(self.check("₹799", [fact])[0].verdict, "needs_review")

    def test_wrong_product_or_market_not_used(self):
        for fact in [replace(self.fact, product="Other"), replace(self.fact, market="US")]:
            self.assertEqual(self.check("₹799", [fact])[0].verdict, "needs_review")

    def test_known_historical_value_is_outdated(self):
        old = replace(self.fact, id="old", amount=Decimal("899"), status="superseded",
                      valid_from=date(2026, 1, 1), valid_to=date(2026, 9, 30))
        self.assertEqual(self.check("₹899", [self.fact, old])[0].verdict, "outdated")

    def test_pending_old_value_is_not_historical_evidence(self):
        old = replace(self.fact, amount=Decimal("799"), status="pending", valid_to=date(2026, 9, 30))
        self.assertEqual(self.check("₹799", [self.fact, old])[0].verdict, "violation")

    def test_conflicting_current_facts_do_not_choose_arbitrarily(self):
        other = replace(self.fact, id="fact-2", amount=Decimal("1099"))
        f = self.check("₹999", [self.fact, other])[0]
        self.assertEqual(f.verdict, "needs_review")
        self.assertIsNone(f.suggested_fix)

    def test_emoji_offsets_slice_original_text(self):
        text = "🎧 Offer ₹799 today"
        f = self.check(text)[0]
        self.assertEqual(text[f.span_start:f.span_end], "₹799")

    def test_supported_inr_formats_and_decimals(self):
        for text in ["₹999", "INR 999.00", "Rs. 999", "Rs 999"]:
            with self.subTest(text=text):
                self.assertEqual(self.check(text)[0].verdict, "supported")
        self.assertEqual(self.check("₹1,099.50")[0].verdict, "violation")

    def test_multiple_prices_return_separate_spans(self):
        text = "Was ₹799. Now ₹999!"
        fs = self.check(text)
        self.assertEqual([f.verdict for f in fs], ["violation", "supported"])
        self.assertEqual([text[f.span_start:f.span_end] for f in fs], ["₹799", "₹999"])

    def test_no_recognised_price_is_not_a_clean_verdict(self):
        self.assertEqual(self.check("Battery lasts 40 hours"), [])
        self.assertEqual(self.check("USD 999"), [])

    def test_inclusive_end_date(self):
        fact = replace(self.fact, valid_to=self.context.publication_date)
        self.assertEqual(self.check("₹999", [fact])[0].verdict, "supported")


if __name__ == "__main__":
    unittest.main()
