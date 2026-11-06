"""py -m examples.attribution_demo. Real bounded attribution, no model calls."""

from datetime import date
from app.services.contracts import ReviewContext
from app.services.factual_checks import check_facts
from evaluation.fixtures import knowledge


def main():
    products,facts,_,_=knowledge()
    context=ReviewContext("Veyra Beat 200","IN",date(2026,11,5))
    texts=["Beat 200 at ₹799 and Air 100 at ₹1499.",
           "Beat 200 and Air 100 at ₹999.",
           "Beat 200 ships in 40 hours with a battery included.",
           "Beat 200 battery life up to 50 hours, delivery in 24 hours.",
           "Air 100 at ₹1499. It has battery life up to 50 hours."]
    for text in texts:
        print("\nDRAFT:",text)
        findings=check_facts(text,context,products,facts,org_id="demo-org",brand_id="veyra")
        for f in findings: print(f"{f.quoted_text!r}: product={f.product_id}; verdict={f.verdict}; fix={f.suggested_fix!r}")
        if not findings:print("No supported numeric specification detected; this is not an approval.")
    print("\nPronouns and genuinely grouped product claims still require review. No content saved or approved.")


if __name__=="__main__":main()
