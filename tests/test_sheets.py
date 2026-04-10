from decimal import Decimal

from rechnungen_poc.models import EmailMessage, InvoiceData
from rechnungen_poc.sheets import map_invoice_to_sheet_row


def test_map_invoice_to_sheet_row_formats_expected_columns() -> None:
    invoice = InvoiceData(
        vendor_name="ACME GmbH",
        invoice_number="R-100",
        invoice_date="2026-04-01",
        due_date="2026-04-15",
        currency="EUR",
        net_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
        gross_amount=Decimal("119.00"),
        iban="DE123",
        reference="PO-77",
        service_period="2026-03",
        needs_review=True,
    )
    email = EmailMessage(
        id="abc",
        subject="Invoice",
        sender="vendor@example.com",
        date="Fri, 10 Apr 2026 10:00:00 +0200",
        body="Attached invoice",
        pdfs=[],
    )

    row = map_invoice_to_sheet_row("CON_ER-2026-0001", invoice, email, "https://drive/link")

    assert row == [
        "CON_ER-2026-0001",
        "2026-04-01",
        "2026-04-15",
        "ACME GmbH",
        "PO-77",
        "100.00",
        "19.00",
        "119.00",
        "EUR",
        "DE123",
        "2026-03",
        "Ja",
        "",
        "",
        "https://drive/link",
        "Fri, 10 Apr 2026 10:00:00 +0200",
        "vendor@example.com",
    ]
