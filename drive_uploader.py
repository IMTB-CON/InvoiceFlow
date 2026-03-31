import io
import os
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "")


def _sanitize(value: str) -> str:
    value = value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    value = value.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
    value = value.replace("ß", "ss")
    value = re.sub(r"[^\w\-]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unbekannt"


def upload_pdf(creds, pdf_bytes: bytes, filename: str, extracted_data: dict) -> str:
    if not DRIVE_FOLDER_ID.strip():
        raise ValueError("DRIVE_FOLDER_ID fehlt. Bitte in .env setzen.")

    service = build("drive", "v3", credentials=creds)

    date_raw = extracted_data.get("invoice_date") or ""
    if date_raw and len(date_raw) == 10 and date_raw[4] == "-" and date_raw[7] == "-":
        date_str = date_raw.replace("-", "")
    else:
        date_str = "unbekannt"

    lieferant = _sanitize(extracted_data.get("vendor_name") or "unbekannt")
    rgnr = _sanitize(extracted_data.get("invoice_number") or "unbekannt")

    new_filename = f"{date_str}_{lieferant}_{rgnr}.pdf"

    file_metadata = {
        "name": new_filename,
        "parents": [DRIVE_FOLDER_ID],
    }
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink",
    ).execute()

    return uploaded.get("webViewLink", "")
