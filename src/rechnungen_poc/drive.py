from __future__ import annotations

import io
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from rechnungen_poc.config import AppConfig
from rechnungen_poc.models import InvoiceData
from rechnungen_poc.utils import sanitize_drive_component


def build_drive_filename(invoice: InvoiceData) -> str:
    date_raw = invoice.invoice_date or ""
    if len(date_raw) == 10 and date_raw[4] == "-" and date_raw[7] == "-":
        date_component = date_raw.replace("-", "")
    else:
        date_component = "unbekannt"

    vendor_component = sanitize_drive_component(invoice.vendor_name or "unbekannt")
    number_component = sanitize_drive_component(invoice.invoice_number or "unbekannt")
    return f"{date_component}_{vendor_component}_{number_component}.pdf"


class DriveUploader:
    def __init__(self, credentials: Any, config: AppConfig) -> None:
        self._config = config
        self._service = build("drive", "v3", credentials=credentials)

    def upload_pdf(self, pdf_bytes: bytes, invoice: InvoiceData) -> str:
        file_metadata = {
            "name": build_drive_filename(invoice),
            "parents": [self._config.drive_folder_id],
        }
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")

        uploaded = self._service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
        ).execute()
        return uploaded.get("webViewLink", "")
