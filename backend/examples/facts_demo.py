"""Run: py -m examples.facts_demo. Fictional multi-product checking demo."""

import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from app.services.contracts import NumericFact, Product, ReviewContext, Source
from app.services.factual_checks import check_facts


def demo_data():
    products = [Product("beat", "demo-org", "veyra", "Veyra Beat 200", ("Beat 200",)),
                Product("air", "demo-org", "veyra", "Veyra Air 100", ("Air 100",))]
    facts = []
    for product, price, battery in [(products[0], "999", "40"), (products[1], "1499", "30")]:
        for attribute, value, unit, qualifier in [("price", price, "INR", "exact"),
            ("battery_life", battery, "hours", "up_to"), ("warranty", "1", "years", "exact")]:
            facts.append(NumericFact(product.id + "-" + attribute, "demo-org", "veyra", 1,
                product.id, attribute, Decimal(value), unit,
                Source("facts-demo", "Fictional Veyra Facts", "section " + product.id,
                       f"{product.name}: {attribute} {qualifier} {value} {unit}"),
                "IN", status="approved", qualifier=qualifier, valid_from=date(2026, 10, 1)))
    return products, facts


def main():
    products, facts = demo_data()
    context = ReviewContext("", "IN", date(2026, 11, 5))
    draft = ("Veyra Beat 200 at ₹799, with battery life up to 50 hours and a 2-year warranty. "
             "Air 100 at ₹1499, with battery life up to 30 hours and a 12-month warranty.")
    findings = check_facts(draft, context, products, facts, org_id="demo-org", brand_id="veyra")
    print(json.dumps({"draft": draft, "findings": [asdict(f) for f in findings]}, ensure_ascii=False, indent=2))
    print("\nSUMMARY")
    for f in findings:
        print(f"{f.product_id}: {f.quoted_text!r} -> {f.verdict}; replacement={f.suggested_fix!r}")
    print("\nAMBIGUOUS EXAMPLE")
    for f in check_facts("Beat 200 and Air 100 at ₹999.", context, products, facts,
                         org_id="demo-org", brand_id="veyra"):
        print(f.verdict + ": " + f.explanation)


if __name__ == "__main__":
    main()
