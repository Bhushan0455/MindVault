"""py -m examples.clarity_demo. Real local screening of fictional rules."""

from dataclasses import asdict, replace
import json

from app.services.clarity import audit_clarity, proposal_is_current
from app.services.contracts import Rule, Source


def main():
    base=Rule("headline","demo-org","veyra","HEADLINE-01",1,"Headlines should be short.",
        Source("guide","Fictional Veyra Guidelines","paragraph 1","Headlines should be short."),status="pending")
    rules=[base,
        replace(base,id="visual",code="VISUAL-01",instruction="Use attractive visuals.",
                source=replace(base.source,location="paragraph 2",excerpt="Use attractive visuals.")),
        replace(base,id="conditional",code="DISC-02",instruction="Include the disclaimer where appropriate.",
                source=replace(base.source,location="paragraph 3",excerpt="Include the disclaimer where appropriate.")),
        replace(base,id="principle",code="TONE-01",instruction="Be approachable.",
                source=replace(base.source,location="paragraph 4",excerpt="Be approachable.")),
        replace(base,id="clear",code="HEADLINE-02",instruction="Headlines must contain no more than 8 words.",
                source=replace(base.source,location="paragraph 5",excerpt="Headlines must contain no more than 8 words."))]
    result=audit_clarity(rules,org_id="demo-org",brand_id="veyra")
    print(json.dumps(asdict(result),ensure_ascii=False,indent=2))
    print(f"\nSUMMARY: {len(result.checked_rule_ids)} rules checked, {len(result.findings)} pending clarity proposals.")
    headline=next(f for f in result.findings if f.rule_id=="headline")
    print("Proposal matches original rule snapshot:",proposal_is_current(base,headline))
    print("Proposal matches after rule text changes:",proposal_is_current(replace(base,instruction="Headlines should be concise."),headline))
    print("The 8-word limit is a proposal, not a source fact. No rule changed, approved or saved.")


if __name__ == "__main__": main()
