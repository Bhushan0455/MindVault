"""py -m examples.fixes_demo. Real checks + explicitly recorded demo decisions."""

from dataclasses import asdict, replace
from datetime import date
from decimal import Decimal
import json

from app.services.checks import check_prices
from app.services.contracts import PriceFact, ReviewContext, Rule, RuleScope, Source
from app.services.fixes import FixDecision, FixError, apply_selected_fixes, body_hash
from app.services.rule_checks import check_rules


def main():
    source = Source("guide", "Fictional Veyra Guidelines", "section 3",
                    "Use affordable instead of cheap. Paid ads require T&C apply. Claims need evidence.")
    terms = Rule("terms", "demo-org", "veyra", "TERM-01", 1, "Avoid cheap", source,
        status="approved", category="terminology", severity="medium",
        forbidden_terms=("cheap",), preferred_terms=(("cheap", "affordable"),))
    disclaimer = replace(terms, id="disc", code="DISC-01", category="disclaimer", severity="high",
        forbidden_terms=(), preferred_terms=(), required_text="T&C apply", scope=RuleScope(content_type=("paid_ad",)))
    claims = replace(terms, id="claims", code="CLAIM-01", category="claims", severity="high",
        forbidden_terms=(), preferred_terms=(), requires_claim_evidence=True)
    rules = [terms, disclaimer, claims]
    context = ReviewContext("Veyra Beat 200", "IN", date(2026,11,5), channel="instagram", content_type="paid_ad")
    fact = PriceFact("price", 1, context.product, "IN", Decimal("999"), "INR", "approved", date(2026,10,1),
        Source("fact-sheet", "Fictional Fact Sheet", "page 2", "Veyra Beat 200 price ₹999"))
    text = "Veyra Beat 200 at ₹799. Discover cheap headphones. Best headphones in India."
    def check(body):
        return [*check_prices(body, context, [fact]), *check_rules(body, context, rules, [],
                    org_id="demo-org", brand_id="veyra").findings]
    findings = check(text)
    # These are explicit fictional human decisions, not automatic accept-all.
    decisions = [FixDecision(f"demo-finding-{i}", "revision-1", f,
        "edited" if f.category == "claims" else "accepted",
        edited_text="Explore" if f.category == "claims" else None) for i,f in enumerate(findings)]
    result = apply_selected_fixes(text, revision_id="revision-1", expected_body_hash=body_hash(text), decisions=decisions)
    print("FICTIONAL HUMAN DECISION DEMO: price/term/disclaimer accepted; claim manually edited to Explore.")
    print("ORIGINAL:", text)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    remaining = [f for f in check(result.body_text) if f.verdict != "supported"]
    print("RECHECK: remaining detected issues =", len(remaining))
    print("STALE TEXT EXAMPLE:")
    try:
        apply_selected_fixes(text+" Changed.", revision_id="revision-1", expected_body_hash=body_hash(text), decisions=decisions)
    except FixError as exc:
        print(exc.code + ": " + exc.detail)
    print("No revision saved or approved. Role A saves a new revision transactionally, then queues a recheck.")


if __name__ == "__main__": main()
