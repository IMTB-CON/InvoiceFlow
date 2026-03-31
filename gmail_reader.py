import base64
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def get_google_credentials():
    credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    token_file = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as token:
            token.write(creds.to_json())
    return creds


def fetch_invoice_emails(creds, max_results=10):
    service = build("gmail", "v1", credentials=creds)
    include_processed = os.getenv("INCLUDE_PROCESSED_EMAILS", "false").lower() in {"1", "true", "yes", "on"}
    query = os.getenv(
        "GMAIL_QUERY",
        "subject:(Rechnung OR Invoice OR Fatura OR Factura OR Fattura OR Faktura OR Счёт) has:attachment newer_than:30d",
    )

    processed_label_id = _get_or_create_label(service, "Verarbeitet")

    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        label_ids = msg.get("labelIds", [])
        if not include_processed and processed_label_id and processed_label_id in label_ids:
            continue

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        subject = headers.get("Subject", "")
        sender = headers.get("From", "")
        date = headers.get("Date", "")
        body = _extract_body(msg["payload"])
        pdfs = _extract_pdfs(service, msg)

        if pdfs:
            emails.append({
                "id": msg_ref["id"],
                "subject": subject,
                "sender": sender,
                "date": date,
                "body": body,
                "pdfs": pdfs,
            })

    return emails


def mark_as_processed(creds, message_id):
    service = build("gmail", "v1", credentials=creds)
    label_id = _get_or_create_label(service, "Verarbeitet")
    if label_id:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]},
        ).execute()


def _get_or_create_label(service, name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == name:
            return label["id"]
    new_label = service.users().labels().create(
        userId="me", body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    ).execute()
    return new_label["id"]


def _extract_body(payload):
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result
    return ""


def _extract_pdfs(service, msg):
    pdfs = []
    _collect_attachments(service, msg["id"], msg["payload"], pdfs)
    return pdfs


def _collect_attachments(service, message_id, payload, pdfs):
    mime = payload.get("mimeType", "")
    filename = payload.get("filename", "")

    if mime == "application/pdf" or (filename and filename.lower().endswith(".pdf")):
        body = payload.get("body", {})
        attachment_id = body.get("attachmentId")
        if attachment_id:
            att = service.users().messages().attachments().get(
                userId="me", messageId=message_id, id=attachment_id
            ).execute()
            pdf_bytes = base64.urlsafe_b64decode(att["data"])
            pdfs.append({"name": filename, "bytes": pdf_bytes})
        else:
            inline_data = body.get("data")
            if inline_data:
                pdf_bytes = base64.urlsafe_b64decode(inline_data)
                pdfs.append({"name": filename or "attachment.pdf", "bytes": pdf_bytes})

    for part in payload.get("parts", []):
        _collect_attachments(service, message_id, part, pdfs)
