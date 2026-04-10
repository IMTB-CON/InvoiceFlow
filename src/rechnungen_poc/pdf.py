from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pdfplumber


logger = logging.getLogger(__name__)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        temp_path = Path(tmp.name)

    try:
        text_parts: list[str] = []
        with pdfplumber.open(temp_path.as_posix()) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                else:
                    logger.debug("No text extracted from PDF page", extra={"page_number": page_number})
        return "\n".join(text_parts)
    finally:
        temp_path.unlink(missing_ok=True)
