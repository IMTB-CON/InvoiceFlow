import os
import re
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME = os.getenv("SHEET_NAME", "Eingangsrechnungen")

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


def _validate_config() -> None:
    if not SPREADSHEET_ID.strip():
        raise ValueError("SPREADSHEET_ID fehlt. Bitte in .env setzen.")
    if not SHEET_NAME.strip():
        raise ValueError("SHEET_NAME fehlt. Bitte in .env setzen.")


def ensure_header(service, spreadsheet_id):
    range_name = f"{SHEET_NAME}!A1:{COLUMN_LETTER}1"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_name
    ).execute()
    existing = result.get("values", [])
    if not existing or existing[0] != HEADERS:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()


def _next_table_invoice_number(service, spreadsheet_id: str) -> str:
    year = str(datetime.now().year)
    prefix = f"CON_ER-{year}-"

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{SHEET_NAME}!A4:A",
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


def append_to_sheet(creds, extracted_data: dict, email_meta: dict, drive_link: str) -> int:
    _validate_config()
    service = build("sheets", "v4", credentials=creds)
    try:
        ensure_header(service, SPREADSHEET_ID)
        table_invoice_number = _next_table_invoice_number(service, SPREADSHEET_ID)

        needs_review = extracted_data.get("needs_review")
        if isinstance(needs_review, bool):
            needs_review = "Ja" if needs_review else ""
        else:
            needs_review = ""

        row = [
            table_invoice_number,
            extracted_data.get("invoice_date") or "",
            extracted_data.get("due_date") or "",
            extracted_data.get("vendor_name") or "",
            extracted_data.get("reference") or "",
            extracted_data.get("net_amount") or "",
            extracted_data.get("tax_amount") or "",
            extracted_data.get("gross_amount") or "",
            extracted_data.get("currency") or "",
            extracted_data.get("iban") or "",
            extracted_data.get("service_period") or "",
            needs_review,
            "",  # Kostenstelle - manuell
            "",  # Status - manuell
            drive_link or "",
            email_meta.get("date") or "",
            email_meta.get("sender") or "",
        ]

        # Nächste freie Zeile in Spalte A ermitteln (ab Zeile 4)
        col_a = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A4:A",
        ).execute()
        next_row = 4 + len(col_a.get("values", []))

        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A{next_row}:{COLUMN_LETTER}{next_row}",
            valueInputOption="RAW",
            body={"values": [row]},
        ).execute()
    except HttpError as e:
        message = str(e)
        if "This operation is not supported for this document" in message:
            raise RuntimeError(
                "Die angegebene SPREADSHEET_ID ist keine native Google-Tabelle. "
                "Bitte eine neue Google Sheet Datei erstellen und die neue ID in .env setzen."
            ) from e
        raise

    return result.get("updatedRows", 0)
