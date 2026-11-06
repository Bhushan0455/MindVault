import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.services.contracts import Product, ReviewContext
from app.services.factual_checks import check_facts
from examples.facts_demo import demo_data


class FactualChecks(unittest.TestCase):
    def setUp(self):
        self.products, self.facts = demo_data()
        self.context = ReviewContext("", "IN", date(2026, 11, 5))

    def check(self, text, products=None, facts=None, context=None):
        return check_facts(text, context or self.context, self.products if products is None else products,
                           self.facts if facts is None else facts, org_id="demo-org", brand_id="veyra")

    def test_separate_sentences_attribute_different_products(self):
        fs = self.check("Beat 200 at ₹799. Air 100 at ₹1499.")
        self.assertEqual([(f.product_id, f.verdict) for f in fs], [("beat", "violation"), ("air", "supported")])
        self.assertEqual(fs[0].suggested_fix, "₹999")

    def test_battery_above_approved_maximum(self):
        f = self.check("Beat 200 battery life up to 50 hours.")[0]
        self.assertEqual((f.verdict, f.suggested_fix, f.fact_id), ("violation", "up to 40 hours", "beat-battery_life"))

    def test_battery_same_maximum_and_qualifier_supported(self):
        f = self.check("Beat 200 has up to 40 hours of battery life.")[0]
        self.assertEqual((f.verdict, f.product_id, f.fact_version), ("supported", "beat", 1))

    def test_battery_without_up_to_is_not_guaranteed_by_maximum(self):
        self.assertEqual(self.check("Beat 200 battery life is 40 hours.")[0].verdict, "needs_review")

    def test_lower_battery_bound_is_not_automatically_substantiated(self):
        self.assertEqual(self.check("Beat 200 battery life up to 20 hours.")[0].verdict, "needs_review")

    def test_year_warranty_mismatch_and_span_replacement(self):
        text = "Beat 200 comes with a 2-year warranty."
        f = self.check(text)[0]
        self.assertEqual((f.verdict, f.suggested_fix), ("violation", "1 year"))
        self.assertEqual(text[f.span_start:f.span_end], "2-year")
        self.assertEqual(text[:f.span_start]+f.suggested_fix+text[f.span_end:], "Beat 200 comes with a 1 year warranty.")

    def test_warranty_months_equal_years(self):
        self.assertEqual(self.check("Air 100 has a 12-month warranty.")[0].verdict, "supported")

    def test_decimal_years_convert_exactly(self):
        facts = [replace(f, value=Decimal("18"), unit="months") if f.id == "beat-warranty" else f for f in self.facts]
        self.assertEqual(self.check("Beat 200 has 1.5 years warranty.", facts=facts)[0].verdict, "supported")

    def test_multi_product_sentence_is_ambiguous(self):
        f = self.check("Beat 200 and Air 100 at ₹999.")[0]
        self.assertEqual(f.verdict, "needs_review")
        self.assertIsNone(f.product_id)
        self.assertIsNone(f.suggested_fix)

    def test_no_product_with_multiple_candidates_is_ambiguous(self):
        self.assertEqual(self.check("Price ₹999.")[0].verdict, "needs_review")

    def test_explicit_selected_product_fallback(self):
        f = self.check("Battery life up to 40 hours.", context=replace(self.context, product="Beat 200"))[0]
        self.assertEqual((f.verdict, f.product_id), ("supported", "beat"))

    def test_unknown_selected_product_does_not_fall_back_to_other_fact(self):
        fs = self.check("Price ₹999.", products=self.products[:1], context=replace(self.context, product="Unknown"))
        self.assertEqual(fs[0].verdict, "needs_review")

    def test_single_product_attribute_fallback(self):
        f = self.check("Price ₹999.", products=self.products[:1])[0]
        self.assertEqual((f.verdict, f.product_id), ("supported", "beat"))

    def test_conflicting_explicit_product_disables_selected_fallback_elsewhere(self):
        f = self.check("Air 100 is available. Price ₹999.", context=replace(self.context, product="Beat 200"))[-1]
        self.assertEqual(f.verdict, "needs_review")

    def test_shared_alias_is_ambiguous(self):
        products = [replace(p, aliases=("Headphones",)) for p in self.products]
        self.assertEqual(self.check("Headphones at ₹999", products=products)[0].verdict, "needs_review")

    def test_longer_canonical_name_wins_over_substring_alias(self):
        products = [self.products[0], replace(self.products[1], aliases=("Veyra",))]
        self.assertEqual(self.check("Veyra Beat 200 at ₹999", products=products)[0].product_id, "beat")

    def test_distant_product_does_not_get_assigned(self):
        self.assertEqual(self.check("Beat 200 " + "word "*25 + "₹999")[0].verdict, "needs_review")

    def test_foreign_product_or_fact_cannot_supply_evidence(self):
        for field in ["org_id", "brand_id"]:
            facts = [replace(f, **{field: "other"}) for f in self.facts]
            self.assertEqual(self.check("Beat 200 at ₹999", facts=facts)[0].verdict, "needs_review")
            products = [replace(p, **{field: "other"}) for p in self.products]
            self.assertEqual(self.check("Beat 200 at ₹999", products=products)[0].verdict, "needs_review")

    def test_pending_wrong_market_and_future_facts_do_not_support(self):
        for changes in [dict(status="pending"), dict(market="US"), dict(valid_from=date(2027, 1, 1)),
                        dict(valid_to=date(2026, 10, 1))]:
            facts = [replace(f, **changes) for f in self.facts]
            self.assertEqual(self.check("Beat 200 at ₹999", facts=facts)[0].verdict, "needs_review")

    def test_conflicting_active_facts_do_not_pick_one(self):
        facts = [*self.facts, replace(self.facts[0], id="other", value=Decimal("799"))]
        self.assertEqual(self.check("Beat 200 at ₹999", facts=facts)[0].verdict, "needs_review")

    def test_historical_numeric_fact(self):
        old = replace(self.facts[2], id="old", value=Decimal("2"), status="superseded", valid_to=date(2026, 10, 1))
        self.assertEqual(self.check("Beat 200 2-year warranty.", facts=[*self.facts, old])[0].verdict, "outdated")

    def test_emoji_offsets_and_supported_dependency(self):
        text = "🎧 Beat 200 battery up to 40 hours."
        f = self.check(text)[0]
        self.assertEqual(text[f.span_start:f.span_end], "up to 40 hours")
        self.assertEqual(f.fact_id, "beat-battery_life")
        self.assertIsNotNone(f.source)

    def test_unrelated_durations_not_checked(self):
        self.assertEqual(self.check("Beat 200 ships in 40 hours. Delivery takes 1 year."), [])

    def test_invalid_approved_unit_or_value_fails_explicitly(self):
        for changes in [dict(unit="years"), dict(value=Decimal("NaN")), dict(value=Decimal("-1"))]:
            with self.assertRaises(ValueError):
                self.check("Beat 200 at ₹999", facts=[replace(self.facts[0], **changes)])

    def test_blank_tenant_identifiers_rejected(self):
        with self.assertRaises(ValueError):
            check_facts("", self.context, [], [], org_id="", brand_id="veyra")


if __name__ == "__main__":
    unittest.main()
