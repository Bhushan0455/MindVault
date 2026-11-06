"""Run from backend/: py -m examples.context_demo"""

from dataclasses import replace
from datetime import date

from app.services.context import resolve_rules
from app.services.contracts import ReviewContext, Rule, RuleScope, Source


def main():
    source = Source("guidelines-demo", "Fictional Veyra Guidelines", "section 3",
                    "Instagram: conversational. Investor decks: formal. Claims need evidence.")
    base = Rule("claim", "demo-org", "veyra", "CLAIM-01", 1,
                "Superlative claims need approved evidence.", source,
                status="approved", authority="non_overridable")
    rules = [base,
        replace(base, id="instagram", code="TONE-IG-02", authority="scoped",
                instruction="Use conversational language for consumers on Instagram.",
                scope=RuleScope(channel=("instagram",), audience=("consumer",))),
        replace(base, id="investors", code="TONE-INV-03", authority="scoped",
                instruction="Use formal language and no exclamation marks in investor decks.",
                scope=RuleScope(channel=("investor_deck",))),
        replace(base, id="pending", code="DRAFT-RULE", status="pending"),
        replace(base, id="expired", code="OLD-CAMPAIGN", effective_to=date(2026, 10, 31))]
    context = ReviewContext("Veyra Beat 200", "IN", date(2026, 11, 5),
                            channel="instagram", audience="consumer", content_type="paid_ad")
    print("SAMPLE TEXT: We're the best in the business!")
    print("This demo SELECTS rules; tone/claim detection comes in later steps.")
    for selected in [context, replace(context, channel="investor_deck", audience="investor")]:
        result = resolve_rules(selected, rules, org_id="demo-org", brand_id="veyra")
        print(f"\nCHANNEL: {selected.channel}")
        print("APPLIED (in checking order):")
        for item in result.applied:
            print(f"  {item.rule.code} v{item.rule.version}: {item.why}")
        print("SKIPPED:")
        for item in result.skipped:
            print(f"  {item.rule.code}: {item.reason}")


if __name__ == "__main__":
    main()
