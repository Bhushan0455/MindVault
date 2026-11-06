"""Milestone 1: evidence-linked INR price checks; no AI or database calls.

Scope: explicit INR prices in a single-product draft. Bare numbers, other
currencies, discounts, bundles, multiple products and pricing exceptions are
outside this first milestone. Unsupported/ambiguous inputs are never labelled
clean: supported findings only describe the price spans actually checked.
"""

from datetime import date
from decimal import Decimal

from .contracts import Finding, PriceFact, ReviewContext
from .numbers import iter_prices


def _effective(fact: PriceFact, day: date) -> bool:
    return fact.valid_from <= day and (fact.valid_to is None or day <= fact.valid_to)


def _money(amount: Decimal) -> str:
    return f"₹{amount:,.0f}" if amount == amount.to_integral_value() else f"₹{amount:,.2f}"


def check_prices(text: str, context: ReviewContext, facts: list[PriceFact]) -> list[Finding]:
    """Return one finding per recognised price, including supported prices.

    Caller must supply facts from ONE authenticated organisation and brand.
    This pure service cannot enforce database permissions. A selected product
    must describe the whole draft; multi-product attribution is a later step.
    Conflicting or missing current facts require human review, not a guess.
    """
    relevant = [
        f for f in facts
        if f.product.casefold() == context.product.casefold()
        and f.market.casefold() == context.market.casefold()
        and f.currency.upper() == "INR"
    ]
    current = [f for f in relevant if f.status == "approved" and _effective(f, context.publication_date)]
    result = []
    for match in iter_prices(text):
        amount = match.value
        base = dict(
            origin="deterministic", category="price", span_start=match.start,
            span_end=match.end, quoted_text=text[match.start:match.end],
        )
        if not context.product.strip() or len(current) != 1:
            reason = "No single approved price is available for the selected product, market and date."
            if len(current) > 1:
                reason = "Multiple approved prices overlap for this product, market and date. Resolve the knowledge conflict."
            result.append(Finding(**base, severity="high", confidence=1.0,
                verdict="needs_review", explanation=reason, suggested_fix=None,
                fact_id=None, fact_version=None, source=None))
            continue
        fact = current[0]
        approved = _money(fact.amount)
        evidence = f"{fact.source.document_title}, {fact.source.location}"
        if amount == fact.amount:
            verdict, severity = "supported", "info"
            explanation = f"This price matches the approved {approved} price ({evidence})."
            fix = None
        else:
            historical_match = any(
                f.amount == amount
                and f.status in ("approved", "expired", "superseded")
                and f.valid_to is not None
                and f.valid_to < context.publication_date
                for f in relevant
            )
            verdict = "outdated" if historical_match else "violation"
            severity = "critical"
            explanation = f"This price does not match the approved {approved} price ({evidence})."
            if historical_match:
                explanation = "This price matches a historical fact. " + explanation
            fix = approved
        result.append(Finding(**base, severity=severity, confidence=1.0,
            verdict=verdict, explanation=explanation, suggested_fix=fix,
            fact_id=fact.id, fact_version=fact.version, source=fact.source))
    return result
