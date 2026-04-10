from rechnungen_poc.drive import build_drive_filename
from rechnungen_poc.models import InvoiceData


def test_build_drive_filename_sanitizes_components() -> None:
    invoice = InvoiceData(
        vendor_name="Müller & Söhne GmbH",
        invoice_number="RG/2026:04?10",
        invoice_date="2026-04-10",
    )

    assert build_drive_filename(invoice) == "20260410_Mueller_Soehne_GmbH_RG_2026_04_10.pdf"


def test_build_drive_filename_falls_back_for_missing_values() -> None:
    invoice = InvoiceData()
    assert build_drive_filename(invoice) == "unbekannt_unbekannt_unbekannt.pdf"
