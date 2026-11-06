"""py -m examples.validator_demo

Explicit SIMULATION of proposed AI output, to exercise validation offline.
This is a development fixture, not a live Gemini response or production fallback.
"""

from dataclasses import asdict, replace
from datetime import date
import json

from app.services.contracts import ReviewContext, Rule, RuleScope, Source
from app.services.validator import validate_ai_findings


def proposed(quote, **changes):
    item = dict(category="tone", quoted_text=quote, rule_code="TONE-INV-03", fact_id=None,
        verdict="violation", severity="high", confidence=0.9,
        explanation="Exclamation marks conflict with the formal investor tone rule.", suggested_fix="Hello")
    item.update(changes)
    return item


def main():
    print("SIMULATION: testing validator with deliberately mixed proposed AI findings. NO API CALL.")
    text = "🎧 Hello! We are the best."
    context = ReviewContext("Veyra Beat 200", "IN", date(2026, 11, 5), channel="investor_deck")
    rule = Rule("tone", "demo-org", "veyra", "TONE-INV-03", 1,
        "Formal investor decks must avoid exclamation marks.",
        Source("guide", "Fictional Guide", "paragraph 3", "Investor decks: formal, no exclamation marks."),
        status="approved", scope=RuleScope(channel=("investor_deck",)))
    claims_rule = replace(rule, id="claims", code="CLAIM-01", instruction="Superlatives require approved evidence.",
        source=Source("guide", "Fictional Guide", "paragraph 4", "Superlative claims need approved evidence."),
        scope=RuleScope(), category="claims", requires_claim_evidence=True)
    response = {"findings": [proposed("Hello!"), proposed("Hello!"),
        proposed("This quote was invented"), proposed("best", rule_code="FAKE-RULE"),
        proposed("best", rule_code="CLAIM-01", category="claims", confidence=0.4,
                 explanation="Uncertain claim interpretation.", suggested_fix="good")]}
    result = validate_ai_findings(text, response, context=context, rules=[rule, claims_rule], facts=[],
                                  org_id="demo-org", brand_id="veyra")
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    print(f"\nSUMMARY: {len(result.findings)} retained findings (one tone violation, one needs_review).")
    print("Validation checks text and provenance, not whether an AI interpretation is correct. No approval or fixes applied.")


if __name__ == "__main__": main()
