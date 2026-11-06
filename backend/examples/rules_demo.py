"""Run: py -m examples.rules_demo from backend/. All source data is fictional."""

import json
from dataclasses import asdict, replace
from datetime import date
from decimal import Decimal

from app.services.checks import check_prices
from app.services.contracts import PriceFact, ReviewContext, Rule, RuleScope, Source
from app.services.rule_checks import check_rules


def main():
    source = Source("guidelines", "Fictional Veyra Guidelines", "section 3",
                    "Avoid cheap; use affordable. Paid ads require T&C apply. Superlatives need evidence.")
    term = Rule("terms", "demo-org", "veyra", "TERM-01", 1,
                "Use affordable instead of cheap.", source, status="approved",
                category="terminology", severity="medium", forbidden_terms=("cheap",),
                preferred_terms=(("cheap", "affordable"),))
    disclaimer = replace(term, id="disclaimer", code="DISC-01", category="disclaimer",
        instruction="Paid ads must include T&C apply.", severity="high", forbidden_terms=(),
        preferred_terms=(), required_text="T&C apply", scope=RuleScope(content_type=("paid_ad",)))
    claims = replace(term, id="claims", code="CLAIM-01", category="claims",
        instruction="Superlative claims require approved evidence.", severity="high",
        authority="non_overridable", forbidden_terms=(), preferred_terms=(), requires_claim_evidence=True)
    context = ReviewContext("Veyra Beat 200", "IN", date(2026, 11, 5),
                            channel="instagram", audience="consumer", content_type="paid_ad")
    fact = PriceFact("price", 1, context.product, "IN", Decimal("999"), "INR", "approved",
        date(2026, 10, 1), Source("fact-sheet", "Fictional Veyra Fact Sheet", "page 2", "Price: ₹999"))
    draft = "Veyra Beat 200 headphones now at just ₹799! Best headphones in India. A cheap deal."
    result = check_rules(draft, context, [term, disclaimer, claims], [], org_id="demo-org", brand_id="veyra")
    findings = [*check_prices(draft, context, [fact]), *result.findings]
    print(json.dumps({"draft": draft, "applied_rules": [i.rule.code for i in result.resolution.applied],
                      "findings": [asdict(f) for f in findings]}, ensure_ascii=False, indent=2))
    print("\nCLEANER DRAFT (manually rewritten, not auto-fixed):")
    corrected = "Veyra Beat 200 headphones at ₹999. An affordable option. T&C apply"
    checked = check_rules(corrected, context, [term, disclaimer, claims], [], org_id="demo-org", brand_id="veyra")
    combined = [*check_prices(corrected, context, [fact]), *checked.findings]
    print(corrected)
    print("Blocking findings:", sum(f.severity in ("critical", "high") and f.verdict != "supported" for f in combined))
    print("These limited checks do not automatically approve content.")


if __name__ == "__main__":
    main()
