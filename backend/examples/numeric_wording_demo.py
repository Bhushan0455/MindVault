"""py -m examples.numeric_wording_demo. Real checks, fictional approved facts."""

from datetime import date
from app.services.contracts import ReviewContext
from app.services.factual_checks import check_facts
from evaluation.fixtures import knowledge


def main():
    products,facts,_,_=knowledge()
    context=ReviewContext("Veyra Beat 200","IN",date(2026,11,5))
    cases=["Beat 200 costs 799 rupees.","Beat 200 costs seven hundred ninety-nine rupees.",
        "Beat 200 costs ₹1,49,999.","Beat 200 has a two-year warranty.",
        "Beat 200 battery life is fifty hours.","Beat 200 battery life is up to forty hours."]
    for text in cases:
        print("\nDRAFT:",text)
        for finding in check_facts(text,context,products,facts,org_id="demo-org",brand_id="veyra"):
            print(f"{finding.quoted_text!r} -> {finding.verdict}; suggested_fix={finding.suggested_fix!r}")
    print("\nNo AI call, database save, automatic fix or approval. These are bounded number-format checks.")


if __name__=="__main__":main()
