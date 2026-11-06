import hashlib
from io import BytesIO
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from docx import Document
from pypdf import PdfReader, PdfWriter

from app.services.extraction import ExtractionError, extract_document
from examples.extraction_demo import sample_docx, sample_pdf


class ExtractionTests(unittest.TestCase):
    def assert_error(self, code, name, data, **kwargs):
        with self.assertRaises(ExtractionError) as raised:
            extract_document(name, data, **kwargs)
        self.assertEqual(raised.exception.code, code)

    def test_utf8_unicode_and_line_references(self):
        result = extract_document("demo.txt", "🎧 Price ₹999\n\nT&C apply\n".encode())
        self.assertEqual([b.location for b in result.blocks], ["line 1", "line 3"])
        self.assertIn("₹999", result.text)
        for block in result.blocks:
            self.assertEqual(result.text[block.start:block.end], block.text)

    def test_utf8_and_utf16_bom(self):
        for encoding in ["utf-8-sig", "utf-16"]:
            self.assertEqual(extract_document("demo.txt", "₹999".encode(encoding)).blocks[0].text, "₹999")

    def test_invalid_encoding_and_binary_text(self):
        self.assert_error("invalid_encoding", "demo.txt", b"\x80")
        self.assert_error("binary_text", "demo.txt", b"text\x00binary")

    def test_empty_and_whitespace_files(self):
        self.assert_error("empty_file", "empty.txt", b"")
        self.assert_error("no_text", "blank.txt", b" \n\t")

    def test_size_limit_and_exact_boundary(self):
        self.assert_error("file_too_large", "a.txt", b"1234", max_upload_bytes=3)
        self.assertEqual(extract_document("a.txt", b"123", max_upload_bytes=3).blocks[0].text, "123")

    def test_unsupported_extensions(self):
        for name in ["image.png", "old.doc", "macro.docm", "noextension"]:
            self.assert_error("unsupported_type", name, b"content")

    def test_filename_basename_and_case(self):
        self.assertEqual(extract_document(r"C:\private\DEMO.TXT", b"Text").filename, "DEMO.TXT")

    def test_hash_is_original_bytes(self):
        data = b" Text\r\n"
        r = extract_document("a.txt", data)
        self.assertEqual(r.content_hash, hashlib.sha256(data).hexdigest())
        self.assertNotEqual(r.content_hash, hashlib.sha256(r.text.encode()).hexdigest())

    def test_pdf_preserves_real_pages_and_offsets(self):
        r = extract_document("demo.pdf", sample_pdf())
        self.assertEqual([b.page for b in r.blocks], [1, 2])
        self.assertIn("[[PAGE 2]]", r.text)
        self.assertIn("INR 999", r.blocks[1].text)
        for block in r.blocks:
            self.assertEqual(r.text[block.start:block.end], block.text)

    def test_blank_pdf_page_warning_does_not_renumber_later_page(self):
        writer = PdfWriter(); writer.add_blank_page(width=595, height=842)
        writer.add_page(PdfReader(BytesIO(sample_pdf())).pages[0])
        data = BytesIO(); writer.write(data)
        result = extract_document("mixed.pdf", data.getvalue())
        self.assertEqual(result.blocks[0].page, 2)
        self.assertTrue(any("Page 1 has no extractable" in w for w in result.warnings))

    def test_all_blank_pdf_is_not_success(self):
        writer = PdfWriter(); writer.add_blank_page(width=595, height=842)
        data = BytesIO(); writer.write(data)
        self.assert_error("no_text", "blank.pdf", data.getvalue())

    def test_encrypted_pdf(self):
        writer = PdfWriter(); writer.add_page(PdfReader(BytesIO(sample_pdf())).pages[0]); writer.encrypt("secret")
        data = BytesIO(); writer.write(data)
        self.assert_error("encrypted_pdf", "locked.pdf", data.getvalue())

    def test_pdf_page_limit(self):
        writer = PdfWriter()
        for _ in range(101):
            writer.add_blank_page(width=595, height=842)
        data = BytesIO(); writer.write(data)
        self.assert_error("extraction_limit", "long.pdf", data.getvalue())

    def test_signature_mismatch(self):
        self.assert_error("type_mismatch", "wrong.pdf", b"not a pdf")
        self.assert_error("type_mismatch", "wrong.docx", b"not a docx")

    def test_docx_body_order_and_honest_locations(self):
        r = extract_document("demo.docx", sample_docx())
        self.assertEqual(r.blocks[0].location, "paragraph 1")
        table_index = next(i for i,b in enumerate(r.blocks) if b.text == "₹999")
        battery_index = next(i for i,b in enumerate(r.blocks) if "Battery life" in b.text)
        self.assertLess(table_index, battery_index)
        self.assertIn("table 1, row 2, cell 2", r.blocks[table_index].location)
        self.assertTrue(all(b.page is None for b in r.blocks))
        self.assertNotIn("[[PAGE", r.text)
        for block in r.blocks:
            self.assertEqual(r.text[block.start:block.end], block.text)

    def test_docx_nested_tables_and_merged_cells(self):
        doc = Document(); t = doc.add_table(rows=1, cols=2)
        cell = t.cell(0,0).merge(t.cell(0,1)); cell.text="Merged text"
        nested=cell.add_table(rows=1, cols=1); nested.cell(0,0).text="Nested content"
        data=BytesIO(); doc.save(data)
        r=extract_document("nested.docx", data.getvalue())
        self.assertEqual(sum(b.text == "Merged text" for b in r.blocks), 1)
        self.assertEqual(sum(b.text == "Nested content" for b in r.blocks), 1)

    def test_zip_is_not_automatically_docx(self):
        data=BytesIO()
        with ZipFile(data,"w") as z: z.writestr("readme.txt", "hi")
        self.assert_error("type_mismatch", "wrong.docx", data.getvalue())

    def test_docx_expansion_limit(self):
        data=BytesIO()
        with ZipFile(data,"w",ZIP_DEFLATED) as z:
            z.writestr("word/document.xml", b"a"*(20*1024*1024+1))
            z.writestr("[Content_Types].xml", "placeholder")
        self.assert_error("extraction_limit", "large.docx", data.getvalue())

    def test_corrupt_docx(self):
        self.assert_error("unreadable_document", "corrupt.docx", b"PKbroken")

    def test_extracted_text_limit(self):
        self.assert_error("extraction_limit", "long.txt", b"a"*1_000_001)


if __name__ == "__main__":
    unittest.main()
