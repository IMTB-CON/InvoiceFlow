import json
import os
import re
import requests


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:27b-128k")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "131072"))


def _call_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": OLLAMA_NUM_CTX},
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get("response", "").strip()


def _extract_json_object(raw: str) -> dict:
    start = raw.find("{")
    if start == -1:
        return {}

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(raw)):
        ch = raw[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = raw[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return {}

    return {}


def is_invoice(text: str) -> bool:
    prompt = (
        "You are a document classifier. Determine if the following document is an invoice "
        "(Rechnung, Invoice, Fatura, Factura, Fattura, Faktura, Счёт, or similar in any language). "
        "Respond with ONLY 'true' or 'false'. "
        "If unsure, respond 'true'. "
        "Documents like delivery notes, quotes, terms, or order confirmations are NOT invoices.\n\n"
        f"Document text:\n{text[:2000]}"
    )
    result = _call_ollama(prompt).strip().lower()
    first_word = result.split()[0] if result else ""
    if first_word in {"true", "yes", "1"}:
        return True
    if first_word in {"false", "no", "0"}:
        return False
    return True


def extract_invoice_data(text: str) -> dict:
    truncated = text[:4000]
    prompt = (
        "Du extrahierst Rechnungsdaten aus Texten.\n\n"
        "WICHTIG:\n"
        "- Antworte ausschließlich im JSON-Format.\n"
        "- Erfinde keine Werte.\n"
        "- Wenn unsicher → null setzen und needs_review = true.\n"
        "- Zahlen nur als Dezimalzahl ausgeben.\n"
        "- Datumswerte im Format YYYY-MM-DD.\n"
        "- Keine Erklärungen außerhalb des JSON.\n\n"
        "FELDDEFINITIONEN:\n\n"
        "vendor_name:\n"
        "Die Organisation, die die Rechnung ausstellt und die Zahlung erwartet.\n"
        "Bevorzuge: Briefkopf (oberer Bereich), Block mit USt-IdNr., Adresse, IBAN, Handelsregister.\n"
        "NICHT: Rechnungsempfänger, Kunde, Lieferadresse.\n\n"
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
        raw = _call_ollama(prompt)
        parsed = _extract_json_object(raw)
        if not parsed:
            print(f"[ERROR] No JSON found in LLM response: {raw[:200]}")
            return {}
        return parsed
    except Exception as e:
        print(f"[ERROR] extract_invoice_data failed: {e}")
        return {}
