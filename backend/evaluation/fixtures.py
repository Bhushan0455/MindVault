"""Fictional approved knowledge used by every evaluation case."""

from dataclasses import replace
from datetime import date

from app.services.contracts import ClaimEvidence,Rule,RuleScope,Source
from examples.facts_demo import demo_data


def knowledge(profile="standard"):
    products,facts=demo_data()
    base=Rule("term","demo-org","veyra","TERM-01",1,"Avoid cheap; use affordable.",
        Source("guide","Fictional Evaluation Guidelines","paragraph 1","Avoid cheap; use affordable."),
        status="approved",category="terminology",severity="medium",forbidden_terms=("cheap",),
        preferred_terms=(("cheap","affordable"),))
    disclaimer=replace(base,id="disc",code="DISC-01",category="disclaimer",severity="high",
        forbidden_terms=(),preferred_terms=(),required_text="T&C apply",scope=RuleScope(content_type=("paid_ad",)),
        source=replace(base.source,location="paragraph 2",excerpt="Paid ads must include T&C apply."))
    claims=replace(base,id="claim",code="CLAIM-01",category="claims",severity="high",authority="non_overridable",
        forbidden_terms=(),preferred_terms=(),requires_claim_evidence=True,
        source=replace(base.source,location="paragraph 3",excerpt="Superlative and comparative claims require approved evidence."))
    tone=replace(base,id="tone",code="TONE-INV-03",category="tone",forbidden_terms=(),preferred_terms=(),
        instruction="Investor decks must use formal language and no exclamation marks.",scope=RuleScope(channel=("investor_deck",)),
        source=replace(base.source,location="paragraph 4",excerpt="Investor decks must use formal language and no exclamation marks."))
    evidence=[]
    if profile=="no_price":facts=[f for f in facts if not(f.product_id=="beat" and f.attribute=="price")]
    elif profile=="conflicting_price":facts.append(replace(facts[0],id="price-conflict",value=facts[0].value+100))
    elif profile=="supported_claim":
        evidence=[ClaimEvidence("claim-proof","demo-org","veyra",1,"Veyra Beat 200","IN","Best headphones in India.",
            Source("claim-sheet","Fictional Approved Claims","paragraph 1","Best headphones in India."),status="approved",
            valid_from=date(2026,10,1))]
    elif profile!="standard":raise ValueError("Unknown knowledge profile.")
    return products,facts,[base,disclaimer,claims,tone],evidence
