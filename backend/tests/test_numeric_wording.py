from datetime import date
from decimal import Decimal
import unittest

from app.services.contracts import ReviewContext
from app.services.factual_checks import check_facts
from app.services.numbers import iter_prices,parse_number
from app.services.ai_review import run_review
from evaluation.fixtures import knowledge


class NumericWordingTests(unittest.TestCase):
    def setUp(self):
        self.products,self.facts,self.rules,self.evidence=knowledge()
        self.context=ReviewContext("Veyra Beat 200","IN",date(2026,11,5),content_type="social_post")

    def check(self,text):
        return check_facts(text,self.context,self.products,self.facts,org_id="demo-org",brand_id="veyra")

    def test_cardinals_cover_documented_range(self):
        for raw,value in [("zero",0),("nineteen",19),("twenty-one",21),("forty two",42),
            ("ninety nine",99),("one hundred",100),("one hundred and five",105),
            ("nine hundred ninety-nine",999)]:
            with self.subTest(raw=raw):self.assertEqual(parse_number(raw),Decimal(value))

    def test_grouped_and_decimal_digit_amounts(self):
        for raw,value in [("1,49,999",149999),("12,34,567",1234567),("1,234,567",1234567),
                          ("999.50",Decimal("999.50"))]:
            self.assertEqual(parse_number(raw),Decimal(value))

    def test_entire_number_grammar_required(self):
        for raw in ["one thousand","one lakh","twenty twenty","one point five","-2","half","1/2",
                    "1,49,99","12,345,67","one hundred and"]:
            with self.subTest(raw=raw),self.assertRaises(ValueError):parse_number(raw)

    def test_suffix_rupees_and_prefix_word_amount(self):
        for text,quote in [("Beat 200 costs 275 rupees.","275 rupees"),
            ("Beat 200 costs INR two hundred seventy-five.","INR two hundred seventy-five")]:
            f=self.check(text)[0]
            self.assertEqual((f.quoted_text,f.verdict,f.suggested_fix),(quote,"violation","₹999"))

    def test_supported_worded_price_preserves_fact_dependency(self):
        f=self.check("Beat 200 costs nine hundred ninety-nine rupees.")[0]
        self.assertEqual((f.verdict,f.fact_id),("supported","beat-price"))

    def test_indian_price_span_and_full_replacement(self):
        text="🎧 Beat 200 costs ₹12,34,567.50 today."
        f=self.check(text)[0]
        self.assertEqual(text[f.span_start:f.span_end],"₹12,34,567.50")
        self.assertEqual(text[:f.span_start]+f.suggested_fix+text[f.span_end:],"🎧 Beat 200 costs ₹999 today.")

    def test_worded_battery_above_maximum(self):
        f=self.check("Beat 200 battery life up to sixty-five hours.")[0]
        self.assertEqual((f.verdict,f.quoted_text,f.suggested_fix),("violation","up to sixty-five hours","up to 40 hours"))

    def test_worded_maximum_supported_but_exact_claim_requires_review(self):
        self.assertEqual(self.check("Beat 200 battery up to forty hours.")[0].verdict,"supported")
        self.assertEqual(self.check("Beat 200 battery forty hours.")[0].verdict,"needs_review")

    def test_worded_warranty_months_and_years(self):
        self.assertEqual(self.check("Beat 200 has a twelve-month warranty.")[0].verdict,"supported")
        f=self.check("Beat 200 has a three-year warranty.")[0]
        self.assertEqual((f.verdict,f.suggested_fix),("violation","1 year"))

    def test_worded_hundred_duration(self):
        f=self.check("Beat 200 battery life one hundred and twenty hours.")[0]
        self.assertEqual((f.quoted_text,f.verdict),("one hundred and twenty hours","violation"))

    def test_unsupported_word_numbers_not_partially_recovered(self):
        for text in ["Beat 200 warranty one thousand five years.",
                     "Beat 200 battery three point five hours.","Beat 200 warranty minus two years.",
                     "Beat 200 battery twenty twenty hours."]:
            with self.subTest(text=text):self.assertEqual(self.check(text),[])

    def test_ranges_and_fractions_not_partially_recovered(self):
        for text in ["Beat 200 warranty 1/2 years.","Beat 200 battery 20–30 hours.",
                     "Beat 200 battery forty to fifty hours.","Beat 200 battery twenty and thirty hours."]:
            with self.subTest(text=text):self.assertEqual(self.check(text),[])

    def test_malformed_currency_grouping_not_partially_parsed(self):
        for text in ["₹1,23,45","1,23,45 rupees","₹999.999"]:
            self.assertEqual(list(iter_prices(text)),[])

    def test_prefix_suffix_combination_not_duplicated(self):
        self.assertEqual(len(list(iter_prices("INR 799 rupees"))),1)

    def test_only_suffix_price_still_checks_actual_value(self):
        r=run_review("Only seven hundred rupees for Beat 200.",context=self.context,products=self.products,
            rules=self.rules,numeric_facts=self.facts,claim_evidence=self.evidence,org_id="demo-org",brand_id="veyra")
        self.assertEqual([(f.category,f.verdict) for f in r.findings],[("price","violation")])

    def test_worded_duration_needs_attribute_subject(self):
        self.assertEqual(self.check("Beat 200 ships in sixty hours."),[])

    def test_ordinary_conjunction_not_mistaken_for_number_range(self):
        self.assertEqual(self.check("Beat 200 has warranty coverage and twelve months of support.")[0].verdict,"supported")

    def test_product_name_number_is_not_price(self):
        self.assertEqual(self.check("Veyra Beat 200 headphones."),[])

    def test_worded_numbers_keep_product_ambiguity_guard(self):
        f=self.check("Beat 200 and Air 100 have two-year warranty.")[0]
        self.assertEqual((f.verdict,f.product_id,f.suggested_fix),("needs_review",None,None))


if __name__=="__main__":unittest.main()
