from dataclasses import replace
from datetime import date
import unittest

from app.services.contracts import Product,ReviewContext
from app.services.factual_checks import check_facts
from evaluation.fixtures import knowledge


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.products,self.facts,_,_=knowledge()
        self.context=ReviewContext("Veyra Beat 200","IN",date(2026,11,5))

    def check(self,text,products=None,facts=None):
        return check_facts(text,self.context,self.products if products is None else products,
            self.facts if facts is None else facts,org_id="demo-org",brand_id="veyra")

    def test_and_clauses_attribute_independent_prices(self):
        fs=self.check("Beat 200 at ₹799 and Air 100 at ₹1499.")
        self.assertEqual([(f.product_id,f.verdict) for f in fs],[("beat","violation"),("air","supported")])

    def test_comma_and_while_connectors(self):
        for separator in [", "," while "," whereas "," but "]:
            fs=self.check("Beat 200 costs ₹999"+separator+"Air 100 costs ₹999.")
            self.assertEqual([(f.product_id,f.verdict) for f in fs],[("beat","supported"),("air","violation")])

    def test_three_independent_product_clauses(self):
        pro=Product("pro","demo-org","veyra","Veyra Pro 300",("Pro 300",))
        facts=[*self.facts,replace(self.facts[0],id="pro-price",product_id="pro")]
        fs=self.check("Beat 200 ₹999 and Air 100 ₹1499 and Pro 300 ₹999.",products=[*self.products,pro],facts=facts)
        self.assertEqual([f.product_id for f in fs],["beat","air","pro"])
        self.assertTrue(all(f.verdict=="supported" for f in fs))

    def test_grouped_subject_one_price_still_ambiguous(self):
        f=self.check("Beat 200 and Air 100 at ₹999.")[0]
        self.assertEqual((f.verdict,f.product_id,f.suggested_fix),("needs_review",None,None))

    def test_grouped_subject_shared_warranty_still_ambiguous(self):
        self.assertEqual(self.check("Beat 200 and Air 100 have two-year warranty.")[0].verdict,"needs_review")

    def test_number_before_product_not_split_by_nearest_guess(self):
        fs=self.check("₹999 for Beat 200 and ₹1499 for Air 100.")
        self.assertTrue(all(f.verdict=="needs_review" for f in fs))

    def test_no_numeric_left_clause_does_not_split(self):
        self.assertEqual(self.check("Beat 200 is available and Air 100 costs ₹1499.")[0].verdict,"needs_review")

    def test_comparative_phrase_not_an_independent_connector(self):
        self.assertEqual(self.check("Beat 200 compared to Air 100 costs ₹999.")[0].verdict,"needs_review")

    def test_shared_alias_stays_ambiguous(self):
        products=[replace(p,aliases=("Audio",)) for p in self.products]
        self.assertEqual(self.check("Audio ₹999 and Air 100 ₹1499.",products=products)[0].verdict,"needs_review")

    def test_numeric_comma_groups_not_clause_boundaries(self):
        fs=self.check("Beat 200 ₹1,49,999 and Air 100 ₹1,499.")
        self.assertEqual([(f.product_id,f.quoted_text) for f in fs],[("beat","₹1,49,999"),("air","₹1,499")])
        self.assertEqual(fs[1].verdict,"supported")

    def test_battery_clauses_choose_correct_facts(self):
        fs=self.check("Beat 200 battery up to 50 hours and Air 100 battery up to 30 hours.")
        self.assertEqual([(f.product_id,f.verdict) for f in fs],[("beat","violation"),("air","supported")])

    def test_price_and_spec_in_each_product_clause(self):
        fs=self.check("Beat 200 ₹799 with 2-year warranty and Air 100 ₹1499 with 1-year warranty.")
        self.assertEqual([f.product_id for f in fs],["beat","beat","air","air"])

    def test_shipping_duration_not_battery_life(self):
        for text in ["Beat 200 ships in 48 hours with a battery included.",
                     "Beat 200 delivery takes 24 hours with a battery included.",
                     "Beat 200 dispatch requires 24 hours with a battery included."]:
            with self.subTest(text=text):self.assertEqual(self.check(text),[])

    def test_shipping_suffix_does_not_become_spec(self):
        self.assertEqual(self.check("Beat 200 includes a battery, with 24 hours for delivery."),[])

    def test_real_battery_claim_not_hidden_by_shipping_elsewhere(self):
        fs=self.check("Beat 200 battery life up to 50 hours, delivery in 24 hours.")
        self.assertEqual([(f.quoted_text,f.verdict) for f in fs],[("up to 50 hours","violation")])

    def test_shipping_then_real_battery_claim(self):
        fs=self.check("Beat 200 ships in 24 hours and battery life is up to 50 hours.")
        self.assertEqual([(f.quoted_text,f.verdict) for f in fs],[("up to 50 hours","violation")])

    def test_duration_attached_to_spec_and_shipping_needs_review(self):
        f=self.check("Beat 200 battery life 40 hours shipping.")[0]
        self.assertEqual((f.verdict,f.suggested_fix),("needs_review",None))

    def test_pronouns_still_not_resolved_across_sentences(self):
        fs=self.check("Air 100 costs ₹1499. It has battery life up to 50 hours.")
        self.assertEqual((fs[-1].verdict,fs[-1].product_id),("needs_review",None))

    def test_selected_product_does_not_override_local_air_clause(self):
        fs=self.check("Beat 200 ₹999 and Air 100 ₹999.")
        self.assertEqual(fs[-1].fact_id,"air-price")

    def test_original_offsets_and_sources_survive_clause_split(self):
        text="🎧 Beat 200 ₹799 and Air 100 ₹1499."
        fs=self.check(text)
        for f in fs:
            self.assertEqual(text[f.span_start:f.span_end],f.quoted_text)
            self.assertIsNotNone(f.source)
        self.assertEqual(fs[0].suggested_fix,"₹999")


if __name__=="__main__":unittest.main()
