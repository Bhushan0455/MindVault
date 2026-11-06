"""Run from backend/: python -m examples.price_demo"""

import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from app.services.checks import check_prices
from app.services.contracts import PriceFact, ReviewContext, Source


def main():
    source = Source("demo-doc", "Fictional Veyra Product Fact Sheet", "page 2",
                    "Veyra Beat 200: India retail price ₹999, valid from 1 October 2026.")
    fact = PriceFact("demo-price", 1, "Veyra Beat 200", "IN", Decimal("999"),
                     "INR", "approved", date(2026, 10, 1), source)
    context = ReviewContext("Veyra Beat 200", "IN", date(2026, 11, 5))
    draft = "Veyra Beat 200 headphones now at just ₹799! Best headphones in India."
    print(json.dumps({"draft": draft, "findings": [asdict(f) for f in check_prices(draft, context, [fact])]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
