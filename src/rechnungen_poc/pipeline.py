from __future__ import annotations

import logging

from rechnungen_poc.config import AppConfig
from rechnungen_poc.drive import DriveUploader
from rechnungen_poc.gmail import GmailService
from rechnungen_poc.google_auth import get_google_credentials
from rechnungen_poc.llm import OllamaClient, extract_invoice_data, flag_own_company_as_vendor, is_invoice
from rechnungen_poc.pdf import extract_pdf_text
from rechnungen_poc.sheets import SheetsWriter


logger = logging.getLogger(__name__)


def run_pipeline(config: AppConfig) -> int:
    logger.info("Starting invoice processing", extra={"dry_run": config.dry_run})
    credentials = get_google_credentials(config)
    gmail_service = GmailService(credentials, config)
    llm_client = OllamaClient(config)
    drive_uploader = DriveUploader(credentials, config)
    sheets_writer = SheetsWriter(credentials, config)

    emails = gmail_service.fetch_invoice_emails()
    total_processed = 0
    total_errors = 0

    for email in emails:
        logger.info(
            "Processing email",
            extra={"subject": email.subject, "sender": email.sender, "pdf_count": len(email.pdfs)},
        )
        for pdf in email.pdfs:
            try:
                text = extract_pdf_text(pdf.content)
                if not is_invoice(text, llm_client):
                    logger.info("Skipping non-invoice PDF", extra={"pdf_name": pdf.name})
                    continue

                invoice = extract_invoice_data(text, llm_client)
                if invoice is None:
                    logger.warning("No invoice data extracted", extra={"pdf_name": pdf.name})
                    continue
                invoice = flag_own_company_as_vendor(invoice, config.own_company_names)

                logger.info(
                    "Invoice extracted",
                    extra={
                        "pdf_name": pdf.name,
                        "vendor_name": invoice.vendor_name,
                        "invoice_date": invoice.invoice_date,
                        "invoice_number": invoice.invoice_number,
                        "reference": invoice.reference,
                        "gross_amount": invoice.gross_amount,
                        "currency": invoice.currency,
                        "needs_review": invoice.needs_review,
                        "review_reason": invoice.review_reason,
                    },
                )

                if config.dry_run:
                    logger.info("Dry run enabled, skipping Drive/Sheets/Gmail writes", extra={"pdf_name": pdf.name})
                    total_processed += 1
                    continue

                drive_link = drive_uploader.upload_pdf(pdf.content, invoice)
                sheets_writer.append_invoice(invoice, email, drive_link)
                total_processed += 1
            except Exception:
                logger.exception("Failed to process PDF", extra={"pdf_name": pdf.name})
                total_errors += 1

        if not config.dry_run:
            try:
                gmail_service.mark_as_processed(email.id)
            except Exception:
                logger.exception("Failed to mark email as processed", extra={"message_id": email.id})
                total_errors += 1

    logger.info(
        "Invoice processing finished",
        extra={
            "processed_count": total_processed,
            "error_count": total_errors,
            "email_count": len(emails),
        },
    )
    return 0 if total_errors == 0 else 1
