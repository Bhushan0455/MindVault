"""py -m examples.knowledge_demo [path] [--ai]. Default: real local extraction."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from app.services.extraction import ExtractionError, extract_document
from app.services.knowledge_extract import extract_candidates


def main():
    parser = argparse.ArgumentParser(description="Extract PENDING source-linked knowledge.")
    parser.add_argument("path", nargs="?")
    parser.add_argument("--ai", action="store_true", help="Explicitly send redacted document blocks to Gemini")
    args = parser.parse_args()
    try:
        if args.path:
            p = Path(args.path)
            with p.open("rb") as file: data = file.read(5*1024*1024+1)
            name = p.name
        else:
            name = "fictional_knowledge.txt"
            data = ("Avoid cheap; use affordable.\nPaid ads must include T&C apply.\n"
                    "Veyra Beat 200: price INR 999.\nVeyra Beat 200: battery life up to 40 hours.\n"
                    "Veyra Beat 200: warranty 1 year.").encode()
        document = extract_document(name, data)
        generator = None
        if args.ai:
            from app.services.llm import GeminiKnowledgeGenerator
            generator = GeminiKnowledgeGenerator(org_id="demo-org", brand_id="veyra")
        result = extract_candidates(document, org_id="demo-org", brand_id="veyra",
                                     document_id="demo-document", generator=generator)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        print(f"\nSUMMARY: {len(result.candidates)} pending candidates; method={result.method}.")
        print("No database writes. Admin must approve scope, dates, products and wording before use.")
    except (ExtractionError, OSError, ValueError) as exc:
        parser.exit(1, f"Knowledge extraction failed: {exc}\n")


if __name__ == "__main__": main()
