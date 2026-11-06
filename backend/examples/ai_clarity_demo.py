"""py -m examples.ai_clarity_demo [--ai]. No simulated AI output in this demo."""

import argparse
from dataclasses import asdict,replace
import json

from app.services.ai_clarity import GeminiClarityGenerator,run_clarity_audit
from app.services.contracts import Rule,Source


def demo_rules():
    base=Rule("headline","demo-org","veyra","HEADLINE-01",1,"Headlines should be short.",
        Source("guide","Fictional Guidelines","paragraph 1","Headlines should be short."),status="pending")
    vague="Use business-friendly wording in technical explanations."
    return [base,replace(base,id="business",code="TONE-02",instruction=vague,
        source=replace(base.source,location="paragraph 2",excerpt=vague))]


def main():
    parser=argparse.ArgumentParser(description="Local clarity checks plus optional source-validated AI proposals.")
    parser.add_argument("--ai",action="store_true",help="Explicitly request real Gemini with privately configured environment variables")
    args=parser.parse_args()
    adapter=GeminiClarityGenerator(org_id="demo-org",brand_id="veyra") if args.ai else None
    result=run_clarity_audit(demo_rules(),org_id="demo-org",brand_id="veyra",generator=adapter)
    print(json.dumps(asdict(result),ensure_ascii=False,indent=2))
    print(f"\nSUMMARY: ai_used={result.ai_used}; ai_status={result.ai_status}; pending proposals={len(result.findings)}")
    if not result.ai_used: print("No AI clarity judgement occurred; only narrow local detectors ran.")
    print("No rule updated or approved. Suggested thresholds and examples require admin review.")


if __name__=="__main__":main()
