"""py -m examples.review_demo [--ai]. No simulated provider in this demo."""

import argparse
from dataclasses import asdict
from datetime import date
import json

from app.services.ai_review import GeminiContentGenerator, run_review
from app.services.contracts import ReviewContext, Rule, RuleScope, Source
from examples.facts_demo import demo_data


def demo_inputs():
    products,facts=demo_data()
    context=ReviewContext("Veyra Beat 200","IN",date(2026,11,5),channel="investor_deck",audience="investor",content_type="presentation")
    rule=Rule("tone-investor","demo-org","veyra","TONE-INV-03",1,
        "Use formal language and no exclamation marks in investor decks.",
        Source("guide","Fictional Veyra Guidelines","section 3","Investor decks: formal, no exclamation marks."),
        status="approved",category="tone",scope=RuleScope(channel=("investor_deck",)))
    return dict(text="Veyra Beat 200 now at ₹799. This offer is totally awesome!",
        context=context,products=products,rules=[rule],numeric_facts=facts,claim_evidence=[],
        org_id="demo-org",brand_id="veyra")


def main():
    parser=argparse.ArgumentParser(description="Deterministic-first content review; AI is optional.")
    parser.add_argument("--ai",action="store_true",help="Request real Gemini analysis using configured environment variables")
    args=parser.parse_args()
    inputs=demo_inputs()
    generator=GeminiContentGenerator(org_id="demo-org",brand_id="veyra") if args.ai else None
    result=run_review(**inputs,generator=generator)
    print(json.dumps(asdict(result),ensure_ascii=False,indent=2,default=str))
    print(f"\nSUMMARY: ai_used={result.ai_used}, ai_status={result.ai_status}, findings={len(result.findings)}")
    if not result.ai_used:
        print("No AI tone judgement was performed. The price finding is deterministic.")
    print("No database records, approvals, fixes or review jobs were created.")


if __name__=="__main__": main()
