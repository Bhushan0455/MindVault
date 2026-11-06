"""Step 5: extract upload bytes with honest source locations; no AI or writes.

Byte limit is checked here, but the HTTP adapter must also limit request bodies
before buffering them. Run parsing in bounded background workers in production.
"""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile


class ExtractionError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code, self.detail = code, detail
        super().__init__(detail)


@dataclass(frozen=True)
class TextBlock:
    location: str
    text: str
    start: int  # into ExtractedDocument.text, Unicode code points
    end: int
    page: int | None = None


@dataclass(frozen=True)
class ExtractedDocument:
    filename: str
    media_type: str
    content_hash: str  # original bytes, not extracted text
    text: str
    blocks: tuple[TextBlock, ...]
    warnings: tuple[str, ...]


_TYPES = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          ".txt": "text/plain"}
_MAX_EXPANDED_DOCX = 20 * 1024 * 1024
_MAX_TEXT = 1_000_000
_MAX_BLOCKS = 10_000


def extract_document(filename: str, data: bytes, *, max_upload_bytes: int = 5 * 1024 * 1024) -> ExtractedDocument:
    """Extract supported body text, not approved rules/facts or rendered layout.

    PDF: real 1-based page numbers; no OCR, password support or guaranteed table
    order. DOCX: body paragraphs/tables, including nested tables, but no rendered
    pages, headers/footers, textboxes, comments or tracked-change interpretation.
    TXT: strict UTF-8 or BOM-marked UTF-16, with original 1-based line references.
    """
    if max_upload_bytes <= 0:
        raise ValueError("max_upload_bytes must be positive.")
    name = PurePosixPath(filename.replace("\\", "/")).name
    ext = PurePosixPath(name).suffix.lower()
    if ext not in _TYPES:
        raise ExtractionError("unsupported_type", "Upload a PDF, DOCX or TXT file.")
    if len(data) > max_upload_bytes:
        raise ExtractionError("file_too_large", f"Upload exceeds the {max_upload_bytes}-byte limit.")
    if not data:
        raise ExtractionError("empty_file", "The uploaded file is empty.")
    raw, warnings = [], []
    extracted_chars = 0

    def append(location, text, page=None):
        nonlocal extracted_chars
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if text:
            extracted_chars += len(text)
            if extracted_chars > _MAX_TEXT:
                raise ExtractionError("extraction_limit", "Extracted text exceeds the character limit.")
            raw.append((location, text, page))
        if len(raw) > _MAX_BLOCKS:
            raise ExtractionError("extraction_limit", "Document has too many text blocks.")

    try:
        if ext == ".pdf":
            if not data.startswith(b"%PDF-"):
                raise ExtractionError("type_mismatch", "This file does not have a PDF signature.")
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise ExtractionError("encrypted_pdf", "Upload an unencrypted PDF; password-protected files are not supported.")
            if len(reader.pages) > 100:
                raise ExtractionError("extraction_limit", "PDFs are limited to 100 pages in this version.")
            for index, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                if not text.strip():
                    warnings.append(f"Page {index} has no extractable text; it may be blank or require OCR.")
                append(f"page {index}", text, index)
            warnings.append("PDF reading order and table alignment may need manual verification; OCR is not included.")
        elif ext == ".docx":
            if not data.startswith(b"PK"):
                raise ExtractionError("type_mismatch", "This file does not have a DOCX/ZIP signature.")
            with ZipFile(BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > 2000 or sum(e.file_size for e in entries) > _MAX_EXPANDED_DOCX:
                    raise ExtractionError("extraction_limit", "DOCX expanded content exceeds the processing limit.")
                if not {"word/document.xml", "[Content_Types].xml"}.issubset(archive.namelist()):
                    raise ExtractionError("type_mismatch", "The ZIP file is not a Word DOCX document.")
            from docx import Document
            from docx.text.paragraph import Paragraph
            document = Document(BytesIO(data))
            def walk(container, prefix="", depth=0):
                if depth > 10:
                    raise ExtractionError("extraction_limit", "Nested tables exceed the processing depth limit.")
                paragraph_number, table_number = 0, 0
                for item in container.iter_inner_content():
                    if isinstance(item, Paragraph):
                        paragraph_number += 1
                        append(prefix + f"paragraph {paragraph_number}", item.text)
                    else:
                        table_number += 1
                        seen_cells = set()
                        for row_number, row in enumerate(item.rows, 1):
                            for cell_number, cell in enumerate(row.cells, 1):
                                if cell._tc in seen_cells:
                                    continue
                                seen_cells.add(cell._tc)
                                walk(cell, prefix + f"table {table_number}, row {row_number}, cell {cell_number}, ", depth+1)
            walk(document)
            warnings.append("DOCX uses body paragraph/table references, not rendered pages. Headers, footers, textboxes, comments and tracked changes require separate review.")
        else:
            try:
                text = data.decode("utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
            except UnicodeError as exc:
                raise ExtractionError("invalid_encoding", "Save the TXT file as UTF-8 or BOM-marked UTF-16.") from exc
            if any(ord(c) < 32 and c not in "\r\n\t" for c in text):
                raise ExtractionError("binary_text", "The TXT upload contains binary control characters.")
            for index, line in enumerate(text.splitlines(), 1):
                append(f"line {index}", line)
    except ExtractionError:
        raise
    except ImportError as exc:
        raise ExtractionError("missing_dependency", "Install the extraction packages: py -m pip install -r requirements.txt") from exc
    except Exception as exc:
        raise ExtractionError("unreadable_document", "The document could not be read. It may be corrupt or unsupported; try exporting it again.") from exc
    if not raw:
        raise ExtractionError("no_text", "No readable text was found. For scanned files, use OCR first or enter knowledge manually.")
    pieces, blocks, offset = [], [], 0
    for location, text, page in raw:
        marker = f"[[PAGE {page}]]" if page is not None else "[[" + location.upper() + "]]"
        prefix = ("\n\n" if pieces else "") + marker + "\n"
        offset += len(prefix)
        start = offset
        offset += len(text)
        if offset > _MAX_TEXT:
            raise ExtractionError("extraction_limit", "Extracted text exceeds the character limit.")
        blocks.append(TextBlock(location, text, start, offset, page))
        pieces.append(prefix + text)
    return ExtractedDocument(name, _TYPES[ext], sha256(data).hexdigest(), "".join(pieces), tuple(blocks), tuple(warnings))
