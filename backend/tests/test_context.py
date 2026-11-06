import unittest
from dataclasses import replace
from datetime import date

from app.services.context import resolve_rules
from app.services.contracts import ReviewContext, Rule, RuleScope, Source


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.context = ReviewContext("Veyra Beat 200", "IN", date(2026, 11, 5),
                                     channel="instagram", audience="consumer", content_type="paid_ad")
        self.rule = Rule("r1", "org1", "brand1", "RULE-01", 1, "Fictional instruction",
                         Source("d1", "Fictional Guide", "section 1", "Instruction"), status="approved")

    def resolve(self, *rules, context=None):
        return resolve_rules(context or self.context, list(rules), org_id="org1", brand_id="brand1")

    def test_general_rule_applies(self):
        result = self.resolve(self.rule)
        self.assertEqual(result.applied[0].rule, self.rule)
        self.assertIn("General rule", result.applied[0].why)

    def test_all_scope_dimensions_must_match(self):
        scope = RuleScope(channel=("instagram",), audience=("consumer",), region=("IN",),
                          content_type=("paid_ad",), campaign=("launch",))
        rule = replace(self.rule, scope=scope)
        result = self.resolve(rule, context=replace(self.context, campaign="launch"))
        self.assertEqual(len(result.applied), 1)
        for dimension, wrong in [("channel", "email"), ("audience", "investor"),
                                 ("region", "US"), ("content_type", "blog"), ("campaign", "other")]:
            with self.subTest(dimension=dimension):
                changed = replace(scope, **{dimension: (wrong,)})
                r = self.resolve(replace(rule, scope=changed), context=replace(self.context, campaign="launch"))
                self.assertEqual(len(r.applied), 0)
                self.assertIn("scope_" + dimension, r.skipped[0].reason)

    def test_multiple_allowed_values_use_or_within_dimension(self):
        self.assertEqual(len(self.resolve(replace(self.rule,
            scope=RuleScope(channel=("email", "instagram")))).applied), 1)

    def test_nonapproved_states_never_apply(self):
        for status in ["pending", "extracted", "rejected", "superseded"]:
            result = self.resolve(replace(self.rule, status=status))
            self.assertEqual(result.applied, ())
            self.assertIn(status, result.skipped[0].reason)

    def test_future_and_expired_dates_skip(self):
        for dates in [dict(effective_from=date(2026, 11, 6)), dict(effective_to=date(2026, 11, 4))]:
            self.assertEqual(len(self.resolve(replace(self.rule, **dates)).skipped), 1)

    def test_effective_boundaries_are_inclusive(self):
        day = self.context.publication_date
        result = self.resolve(replace(self.rule, effective_from=day, effective_to=day))
        self.assertEqual(len(result.applied), 1)

    def test_missing_context_is_not_a_wildcard(self):
        r = replace(self.rule, scope=RuleScope(campaign=("launch",)))
        self.assertIn("Missing context: campaign", self.resolve(r).skipped[0].reason)

    def test_normalisation_of_controlled_tags(self):
        r = replace(self.rule, scope=RuleScope(channel=(" Instagram ",), region=("in",)))
        self.assertEqual(len(self.resolve(r).applied), 1)

    def test_foreign_rules_not_exposed_in_either_list(self):
        result = self.resolve(replace(self.rule, org_id="other"), replace(self.rule, brand_id="other"))
        self.assertEqual((result.applied, result.skipped), ((), ()))

    def test_authority_then_specificity_then_priority(self):
        rules = [replace(self.rule, id="exception", authority="exception", priority=999),
                 replace(self.rule, id="scoped", authority="scoped", priority=999),
                 replace(self.rule, id="general", authority="core", priority=999),
                 replace(self.rule, id="specific-low", scope=RuleScope(channel=("instagram",)), priority=1),
                 replace(self.rule, id="specific-high", scope=RuleScope(channel=("instagram",)), priority=10),
                 replace(self.rule, id="mandatory", authority="non_overridable")]
        self.assertEqual([a.rule.id for a in self.resolve(*rules).applied],
                         ["mandatory", "specific-high", "specific-low", "general", "scoped", "exception"])

    def test_conflicting_instructions_are_both_preserved(self):
        a = replace(self.rule, id="a", instruction="Use emojis")
        b = replace(self.rule, id="b", instruction="Never use emojis")
        self.assertEqual(len(self.resolve(a, b).applied), 2)

    def test_stable_order_independent_of_input_order(self):
        a, b = replace(self.rule, id="a"), replace(self.rule, id="b")
        self.assertEqual(self.resolve(a, b), self.resolve(b, a))

    def test_invalid_dates_and_authority_fail_explicitly(self):
        for r in [replace(self.rule, authority="unknown"), replace(self.rule,
                  effective_from=date(2027, 1, 1), effective_to=date(2026, 1, 1))]:
            with self.assertRaises(ValueError):
                self.resolve(r)

    def test_blank_tenant_identifiers_rejected(self):
        with self.assertRaises(ValueError):
            resolve_rules(self.context, [], org_id="", brand_id="brand1")


if __name__ == "__main__":
    unittest.main()
