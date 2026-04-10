from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class PdfAttachment:
    name: str
    content: bytes


@dataclass(frozen=True)
class EmailMessage:
    id: str
    subject: str
    sender: str
    date: str
    body: str
    pdfs: list[PdfAttachment]


@dataclass(frozen=True)
class InvoiceData:
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    net_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    gross_amount: Decimal | None = None
    iban: str | None = None
    reference: str | None = None
    service_period: str | None = None
    needs_review: bool = False
    review_reason: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InvoiceData":
        return cls(
            vendor_name=_clean_string(payload.get("vendor_name")),
            invoice_number=_clean_string(payload.get("invoice_number")),
            invoice_date=_clean_string(payload.get("invoice_date")),
            due_date=_clean_string(payload.get("due_date")),
            currency=_clean_string(payload.get("currency")),
            net_amount=_to_decimal(payload.get("net_amount")),
            tax_amount=_to_decimal(payload.get("tax_amount")),
            gross_amount=_to_decimal(payload.get("gross_amount")),
            iban=_clean_string(payload.get("iban")),
            reference=_clean_string(payload.get("reference")),
            service_period=_clean_string(payload.get("service_period")),
            needs_review=bool(payload.get("needs_review")),
            review_reason=_clean_string(payload.get("review_reason")),
        )


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None
