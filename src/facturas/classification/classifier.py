import io
from enum import Enum

from pypdf import PdfReader

MIN_CHARS_FOR_STRUCTURED = 200


class DocumentKind(str, Enum):
    STRUCTURED_PDF = "structured_pdf"
    SCANNED = "scanned"


def classify(pdf_bytes: bytes) -> DocumentKind:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    if len(text.strip()) >= MIN_CHARS_FOR_STRUCTURED:
        return DocumentKind.STRUCTURED_PDF
    return DocumentKind.SCANNED
