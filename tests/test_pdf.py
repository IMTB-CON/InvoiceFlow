from unittest.mock import patch

from rechnungen_poc.pdf import extract_pdf_text


class _FakePage:
    def __init__(self, text: str | None) -> None:
        self._text = text

    def extract_text(self) -> str | None:
        return self._text


class _FakePdf:
    def __init__(self, pages: list[_FakePage]) -> None:
        self.pages = pages

    def __enter__(self) -> "_FakePdf":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_extract_pdf_text_joins_page_text_and_skips_empty_pages() -> None:
    fake_pdf = _FakePdf([_FakePage("Page 1"), _FakePage(None), _FakePage("Page 3")])

    with patch("rechnungen_poc.pdf.pdfplumber.open", return_value=fake_pdf):
        text = extract_pdf_text(b"%PDF-1.4")

    assert text == "Page 1\nPage 3"
