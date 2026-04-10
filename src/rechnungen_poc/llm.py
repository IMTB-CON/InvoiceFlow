from __future__ import annotations

import dataclasses
import json
import logging
from typing import Any

import requests

from rechnungen_poc.config import AppConfig
from rechnungen_poc.models import InvoiceData


logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def call(self, prompt: str) -> str:
        payload = {
            "model": self._config.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": self._config.ollama_num_ctx},
        }
        response = requests.post(
            self._config.ollama_url,
            json=payload,
            timeout=self._config.ollama_timeout_seconds,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()


def extract_json_object(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    if start == -1:
        return {}

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(raw)):
        char = raw[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = raw[start : index + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON object from LLM output")
                    return {}

    return {}


def is_invoice(text: str, llm_client: OllamaClient) -> bool:
    prompt = (
        "You are a document classifier. Determine if the following document is an invoice "
        "(Rechnung, Invoice, Fatura, Factura, Fattura, Faktura, Счёт, or similar in any language). "
        "Respond with ONLY 'true' or 'false'. "
        "If unsure, respond 'true'. "
        "Documents like delivery notes, quotes, terms, or order confirmations are NOT invoices.\n\n"
        f"Document text:\n{text[:2000]}"
    )
    result = llm_client.call(prompt).strip().lower()
    first_word = result.split()[0] if result else ""
    if first_word in {"true", "yes", "1"}:
        return True
    if first_word in {"false", "no", "0"}:
        return False
    return True


def extract_invoice_data(text: str, llm_client: OllamaClient) -> InvoiceData | None:
    truncated = text[:4000]
    prompt = (
        "Du extrahierst Rechnungsdaten aus Texten.\n\n"
        "WICHTIG:\n"
        "- Antworte ausschließlich im JSON-Format.\n"
        "- Erfinde keine Werte.\n"
        "- Wenn unsicher -> null setzen und needs_review = true.\n"
        "- Zahlen nur als Dezimalzahl ausgeben.\n"
        "- Datumswerte im Format YYYY-MM-DD.\n"
        "- Keine Erklärungen außerhalb des JSON.\n\n"
        "FELDDEFINITIONEN:\n\n"
        "vendor_name:\n"
        "Die Organisation, die die Rechnung ausstellt und die Zahlung erwartet (= Lieferant/Auftragnehmer).\n"
        "Bevorzuge: Briefkopf (oberer Bereich), Block mit USt-IdNr., Adresse, IBAN, Handelsregister.\n"
        "NICHT: Rechnungsempfänger, Kunde, Auftraggeber, Lieferadresse.\n"
        "WICHTIG: Der Empfänger dieser Rechnung ist NIEMALS der vendor_name.\n"
        "Falls nur der Empfänger erkennbar ist und kein externer Aussteller, setze vendor_name = null.\n\n"
        "reference:\n"
        "Geschäftliche Zuordnungsnummer, z. B.: Referenz, Kundenreferenz, Bestellnummer,\n"
        "Auftragsnummer, PO Number, Customer Reference, Ihr Zeichen, Vorgangsnummer, Kostenstelle.\n"
        "Wenn mehrere vorhanden: wichtigste externe Referenz wählen (Bestellnummer > Kundennummer).\n\n"
        "FELDER:\n"
        "vendor_name, invoice_number, invoice_date, due_date, currency,\n"
        "net_amount, tax_amount, gross_amount, iban, reference,\n"
        "service_period, needs_review, review_reason\n\n"
        f"Rechnungstext:\n{truncated}"
    )
    try:
        raw = llm_client.call(prompt)
        parsed = extract_json_object(raw)
        if not parsed:
            logger.error("No JSON found in LLM response", extra={"raw_preview": raw[:200]})
            return None
        return InvoiceData.from_dict(parsed)
    except Exception:
        logger.exception("Invoice extraction failed")
        return None


def flag_own_company_as_vendor(invoice: InvoiceData, own_company_names: frozenset[str]) -> InvoiceData:
    """Return a corrected InvoiceData if vendor_name matches one of the recipient's own company names.

    Matching is case-insensitive substring: each entry in own_company_names is checked against
    vendor_name so that short tokens like 'IMTB' catch longer variants like 'IMTB Consulting GmbH'.
    """
    if not own_company_names or not invoice.vendor_name:
        return invoice

    vendor_lower = invoice.vendor_name.lower()
    matched = next(
        (name for name in own_company_names if name.lower() in vendor_lower or vendor_lower in name.lower()),
        None,
    )
    if matched is None:
        return invoice

    reason = (
        f"vendor_name '{invoice.vendor_name}' stimmt mit eigenem Unternehmen '{matched}' überein "
        "– manuell prüfen und korrekten Lieferanten eintragen."
    )
    existing_reason = invoice.review_reason
    combined_reason = f"{existing_reason} | {reason}" if existing_reason else reason

    logger.warning(
        "vendor_name matches own company – clearing field and flagging for review",
        extra={"vendor_name": invoice.vendor_name, "matched": matched},
    )
    return dataclasses.replace(
        invoice,
        vendor_name=None,
        needs_review=True,
        review_reason=combined_reason,
    )
