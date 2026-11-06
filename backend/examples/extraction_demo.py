"""py -m examples.extraction_demo [path/to/file.pdf]

Without a path, generates tiny fictional PDF/DOCX/TXT samples in memory only.
"""

import argparse
from dataclasses import asdict
from io import BytesIO
import json
from pathlib import Path

from app.services.extraction import ExtractionError, extract_document


def sample_pdf():
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    for line in ["Fictional Veyra Guidelines: Avoid cheap; use affordable.",
                 "Fictional facts: Veyra Beat 200 price INR 999. Warranty 1 year."]:
        page = writer.add_blank_page(width=595, height=842)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
            DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 10 Tf 40 780 Td ({line}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO(); writer.write(output)
    return output.getvalue()


def sample_docx():
    from docx import Document
    doc = Document()
    doc.add_paragraph("Fictional Veyra Guidelines")
    doc.add_paragraph("Paid ads must include T&C apply.")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Product"; table.cell(0, 1).text = "Approved price"
    table.cell(1, 0).text = "Veyra Beat 200"; table.cell(1, 1).text = "₹999"
    doc.add_paragraph("Battery life: up to 40 hours.")
    output = BytesIO(); doc.save(output)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Extract document text with source references.")
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    try:
        if args.path:
            path = Path(args.path)
            # Bounded read, even when the selected local file is very large.
            with path.open("rb") as f:
                samples = [(path.name, f.read(5 * 1024 * 1024 + 1))]
        else:
            samples = [("fictional_guidelines.txt", "Avoid cheap; use affordable.\n\nApproved price ₹999.".encode()),
                       ("fictional_guidelines.pdf", sample_pdf()), ("fictional_facts.docx", sample_docx())]
        for name, data in samples:
            print(json.dumps(asdict(extract_document(name, data)), ensure_ascii=False, indent=2))
        print("\nText extracted only. No rules or facts have been approved or saved.")
    except ExtractionError as exc:
        parser.exit(1, f"{exc.code}: {exc.detail}\n")
    except ImportError:
        parser.exit(1, "Install packages first: py -m pip install -r requirements.txt\n")
    except OSError as exc:
        parser.exit(1, f"Cannot open file: {exc}\n")


if __name__ == "__main__":
    main()
