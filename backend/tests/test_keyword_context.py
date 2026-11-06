from dataclasses import replace
import unittest

from app.services.rule_checks import check_rules
from evaluation.fixtures import knowledge
from app.services.contracts import ReviewContext
from app.services.ai_review import run_review
from datetime import date


class KeywordContextTests(unittest.TestCase):
    def setUp(self):
        _,_,self.rules,_=knowledge()
        self.context=ReviewContext("Veyra Beat 200","IN",date(2026,11,5),channel="instagram",content_type="social_post")

    def check(self,text):
        return check_rules(text,self.context,self.rules,[],org_id="demo-org",brand_id="veyra").findings

    def claims(self,text):return [f for f in self.check(text) if f.category=="claims"]

    def test_direct_negative_is_not_superiority_claim(self):
        for text in ["These are not the fastest headphones.","This isn't the best choice.",
                     "This is not guaranteed to last forever."]:
            with self.subTest(text=text):self.assertEqual(self.claims(text),[])

    def test_positive_claims_still_flagged(self):
        for text in ["The best headphones.","Guaranteed performance.","The fastest headphones."]:
            self.assertEqual(len(self.claims(text)),1)

    def test_not_only_does_not_hide_positive_claim(self):
        for text in ["Not only the best headphones, but affordable.","These are not only unbeatable."]:
            self.assertTrue(self.claims(text))

    def test_double_negation_not_silently_suppressed(self):
        self.assertTrue(self.claims("This is not not the best."))

    def test_negation_does_not_hide_later_positive_claim(self):
        fs=self.claims("Not the cheapest, but the best headphones.")
        self.assertEqual([f.quoted_text for f in fs],["best"])

    def test_negation_does_not_carry_across_sentences(self):
        self.assertEqual([f.quoted_text for f in self.claims("It is not. Best headphones available.")],["Best"])

    def test_only_currency_amount_is_not_exclusivity(self):
        for text in ["Only ₹899 today.","Only INR 999.","Only Rs. 999."]:
            self.assertEqual(self.claims(text),[])

    def test_only_product_still_needs_evidence(self):
        self.assertEqual([f.quoted_text for f in self.claims("The only headphones you need.")],["only"])

    def test_best_practices_is_not_product_superiority(self):
        self.assertEqual(self.claims("Review best practices for charging."),[])
        self.assertEqual(self.claims("Use the best practice for storage."),[])

    def test_best_practices_does_not_hide_another_best_claim(self):
        fs=self.claims("Follow best practices. Buy the best headphones.")
        self.assertEqual([f.quoted_text for f in fs],["best"])

    def test_volume_operating_instruction_is_not_guarantee(self):
        for text in ["Adjust headphone volume to 100%.","Set volume at 100%."]:
            self.assertEqual(self.claims(text),[])

    def test_100_percent_performance_still_flagged(self):
        self.assertEqual([f.quoted_text for f in self.claims("100% satisfaction.")],["100%"])
        self.assertEqual([f.quoted_text for f in self.claims("Our headphone volume is 100% better.")],["100%"])

    def test_policy_discussion_of_term_not_treated_as_product_description(self):
        for text in ["The term ‘cheap’ is disallowed by our policy.","The word cheap is banned by the terminology guide."]:
            self.assertEqual([f for f in self.check(text) if f.category=="terminology"],[])

    def test_quoted_advertising_term_is_still_flagged(self):
        self.assertEqual([f.quoted_text for f in self.check("Buy our 'cheap' headphones.") if f.category=="terminology"],["cheap"])

    def test_policy_discussion_does_not_hide_a_second_promotional_use(self):
        fs=self.check("The word 'cheap' is forbidden by our policy; buy cheap headphones.")
        self.assertEqual([f.quoted_text for f in fs if f.category=="terminology"],["cheap"])

    def test_only_wrong_price_still_produces_numeric_violation(self):
        products,facts,rules,evidence=knowledge()
        result=run_review("Only ₹799 for Beat 200.",context=self.context,products=products,rules=rules,
            numeric_facts=facts,claim_evidence=evidence,org_id="demo-org",brand_id="veyra")
        self.assertEqual([(f.category,f.verdict,f.quoted_text) for f in result.findings],[("price","violation","₹799")])

    def test_negated_superlative_does_not_disable_terminology_check(self):
        fs=self.check("Not the best, but cheap headphones.")
        self.assertEqual([(f.category,f.quoted_text) for f in fs],[("terminology","cheap")])


if __name__=="__main__":unittest.main()
