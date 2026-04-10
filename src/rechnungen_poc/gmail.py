from __future__ import annotations

import base64
import logging
from typing import Any

from googleapiclient.discovery import build

from rechnungen_poc.config import AppConfig
from rechnungen_poc.models import EmailMessage, PdfAttachment


logger = logging.getLogger(__name__)


class GmailService:
    def __init__(self, credentials: Any, config: AppConfig) -> None:
        self._config = config
        self._service = build("gmail", "v1", credentials=credentials)

    def fetch_invoice_emails(self) -> list[EmailMessage]:
        processed_label_id = self._get_or_create_label(self._config.processed_label_name)
        results = self._service.users().messages().list(
            userId="me",
            q=self._config.gmail_query,
            maxResults=self._config.gmail_max_results,
        ).execute()

        emails: list[EmailMessage] = []
        for message_ref in results.get("messages", []):
            message = self._service.users().messages().get(
                userId="me",
                id=message_ref["id"],
                format="full",
            ).execute()

            label_ids = message.get("labelIds", [])
            if (
                not self._config.include_processed_emails
                and processed_label_id
                and processed_label_id in label_ids
            ):
                continue

            headers = {header["name"]: header["value"] for header in message["payload"].get("headers", [])}
            pdfs = self._extract_pdfs(message)

            if pdfs:
                emails.append(
                    EmailMessage(
                        id=message_ref["id"],
                        subject=headers.get("Subject", ""),
                        sender=headers.get("From", ""),
                        date=headers.get("Date", ""),
                        body=self._extract_body(message["payload"]),
                        pdfs=pdfs,
                    )
                )

        logger.info("Fetched invoice candidate emails", extra={"email_count": len(emails)})
        return emails

    def mark_as_processed(self, message_id: str) -> None:
        label_id = self._get_or_create_label(self._config.processed_label_name)
        if not label_id:
            return
        self._service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]},
        ).execute()

    def _get_or_create_label(self, name: str) -> str:
        labels = self._service.users().labels().list(userId="me").execute().get("labels", [])
        for label in labels:
            if label["name"] == name:
                return label["id"]
        created = self._service.users().labels().create(
            userId="me",
            body={
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        ).execute()
        return created["id"]

    def _extract_body(self, payload: dict[str, Any]) -> str:
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        for part in payload.get("parts", []):
            result = self._extract_body(part)
            if result:
                return result

        return ""

    def _extract_pdfs(self, message: dict[str, Any]) -> list[PdfAttachment]:
        pdfs: list[PdfAttachment] = []
        self._collect_attachments(message["id"], message["payload"], pdfs)
        return pdfs

    def _collect_attachments(
        self,
        message_id: str,
        payload: dict[str, Any],
        pdfs: list[PdfAttachment],
    ) -> None:
        mime_type = payload.get("mimeType", "")
        filename = payload.get("filename", "")

        if mime_type == "application/pdf" or (filename and filename.lower().endswith(".pdf")):
            body = payload.get("body", {})
            attachment_id = body.get("attachmentId")
            if attachment_id:
                attachment = self._service.users().messages().attachments().get(
                    userId="me",
                    messageId=message_id,
                    id=attachment_id,
                ).execute()
                pdfs.append(
                    PdfAttachment(
                        name=filename or "attachment.pdf",
                        content=base64.urlsafe_b64decode(attachment["data"]),
                    )
                )
            else:
                inline_data = body.get("data")
                if inline_data:
                    pdfs.append(
                        PdfAttachment(
                            name=filename or "attachment.pdf",
                            content=base64.urlsafe_b64decode(inline_data),
                        )
                    )

        for part in payload.get("parts", []):
            self._collect_attachments(message_id, part, pdfs)
