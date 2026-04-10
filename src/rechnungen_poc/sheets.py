from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from rechnungen_poc.config import AppConfig
from rechnungen_poc.models import EmailMessage, InvoiceData
from rechnungen_poc.utils import decimal_to_sheet_value


logger = logging.getLogger(__name__)

HEADERS = [
    "Rechnungsnummer",
    "Rg.-Datum",
    "Fällig am",
    "Lieferant",
    "Referenz",
    "Netto",
    "MwSt.",
    "Summe Brutto",
    "Währung",
    "IBAN",
    "Leistungszeitraum",
    "Prüfung nötig",
    "Kostenstelle",
    "Status",
    "Drive-Link",
    "E-Mail Datum",
    "E-Mail Absender",
]

COLUMN_COUNT = len(HEADERS)
COLUMN_LETTER = chr(ord("A") + COLUMN_COUNT - 1)


def map_invoice_to_sheet_row(
    table_invoice_number: str,
    invoice: InvoiceData,
    email: EmailMessage,
    drive_link: str,
) -> list[str]:
    needs_review = "Ja" if invoice.needs_review else ""
    return [
        table_invoice_number,
        invoice.invoice_date or "",
        invoice.due_date or "",
        invoice.vendor_name or "",
        invoice.reference or "",
        decimal_to_sheet_value(invoice.net_amount),
        decimal_to_sheet_value(invoice.tax_amount),
        decimal_to_sheet_value(invoice.gross_amount),
        invoice.currency or "",
        invoice.iban or "",
        invoice.service_period or "",
        needs_review,
        "",
        "",
        drive_link or "",
        email.date or "",
        email.sender or "",
    ]


class SheetsWriter:
    def __init__(self, credentials: Any, config: AppConfig) -> None:
        self._config = config
        self._service = build("sheets", "v4", credentials=credentials)

    def ensure_header(self) -> None:
        range_name = f"{self._config.sheet_name}!A1:{COLUMN_LETTER}1"
        result = self._service.spreadsheets().values().get(
            spreadsheetId=self._config.spreadsheet_id,
            range=range_name,
        ).execute()
        existing = result.get("values", [])
        if not existing or existing[0] != HEADERS:
            self._service.spreadsheets().values().update(
                spreadsheetId=self._config.spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": [HEADERS]},
            ).execute()

    def append_invoice(self, invoice: InvoiceData, email: EmailMessage, drive_link: str) -> int:
        try:
            self.ensure_header()
            table_invoice_number = self._next_table_invoice_number()
            row = map_invoice_to_sheet_row(table_invoice_number, invoice, email, drive_link)

            col_a = self._service.spreadsheets().values().get(
                spreadsheetId=self._config.spreadsheet_id,
                range=f"{self._config.sheet_name}!A4:A",
            ).execute()
            next_row = 4 + len(col_a.get("values", []))

            result = self._service.spreadsheets().values().update(
                spreadsheetId=self._config.spreadsheet_id,
                range=f"{self._config.sheet_name}!A{next_row}:{COLUMN_LETTER}{next_row}",
                valueInputOption="RAW",
                body={"values": [row]},
            ).execute()
        except HttpError as exc:
            if "This operation is not supported for this document" in str(exc):
                raise RuntimeError(
                    "Die angegebene SPREADSHEET_ID ist keine native Google-Tabelle. "
                    "Bitte eine neue Google Sheet Datei erstellen und die neue ID in .env setzen."
                ) from exc
            raise

        logger.info("Appended invoice row to sheet", extra={"updated_rows": result.get("updatedRows", 0)})
        return result.get("updatedRows", 0)

    def _next_table_invoice_number(self) -> str:
        year = str(datetime.now().year)
        prefix = f"CON_ER-{year}-"
        result = self._service.spreadsheets().values().get(
            spreadsheetId=self._config.spreadsheet_id,
            range=f"{self._config.sheet_name}!A4:A",
        ).execute()
        rows = result.get("values", [])

        max_number = 0
        pattern = re.compile(rf"^{re.escape(prefix)}(\d{{4}})$")
        for row in rows:
            if not row:
                continue
            value = (row[0] or "").strip()
            match = pattern.match(value)
            if match:
                max_number = max(max_number, int(match.group(1)))

        return f"{prefix}{max_number + 1:04d}"
