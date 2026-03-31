import os
from dotenv import load_dotenv

load_dotenv()

from gmail_reader import get_google_credentials, fetch_invoice_emails, mark_as_processed
from pdf_extractor import extract_pdf_text
from llm_extractor import is_invoice, extract_invoice_data
from sheets_writer import append_to_sheet
from drive_uploader import upload_pdf


def main():
    print("Starte Eingangsrechnungen-Verarbeitung...")

    creds = get_google_credentials()
    max_results = int(os.getenv("GMAIL_MAX_RESULTS", "10"))

    emails = fetch_invoice_emails(creds, max_results=max_results)
    print(f"{len(emails)} E-Mail(s) zur Verarbeitung gefunden.")

    total_processed = 0
    total_errors = 0

    for email in emails:
        print(f"\n--- E-Mail: {email['subject']} ({email['sender']}) ---")

        for pdf in email["pdfs"]:
            pdf_name = pdf["name"]
            try:
                text = extract_pdf_text(pdf["bytes"])

                if not is_invoice(text):
                    print(f"  [SKIP] Kein Rechnungsdokument: {pdf_name}")
                    continue

                print(f"  [OK] Rechnung erkannt: {pdf_name}")

                extracted = extract_invoice_data(text)
                if not extracted:
                    print(f"  [WARN] Keine Daten extrahiert für: {pdf_name}")
                    continue

                print(f"       Lieferant:  {extracted.get('vendor_name')}")
                print(f"       Datum:      {extracted.get('invoice_date')}")
                print(f"       Nummer:     {extracted.get('invoice_number')}")
                print(f"       Referenz:   {extracted.get('reference')}")
                print(f"       Brutto:     {extracted.get('gross_amount')} {extracted.get('currency') or ''}")
                if extracted.get('needs_review'):
                    print(f"       [PRÜFUNG]   {extracted.get('review_reason')}")

                drive_link = upload_pdf(creds, pdf["bytes"], pdf_name, extracted)
                print(f"       Drive:      {drive_link}")

                append_to_sheet(creds, extracted, email, drive_link)
                total_processed += 1

            except Exception as e:
                print(f"  [ERROR] Fehler bei {pdf_name}: {e}")
                total_errors += 1

        try:
            mark_as_processed(creds, email["id"])
        except Exception as e:
            print(f"  [ERROR] Konnte E-Mail nicht als verarbeitet markieren: {e}")

    print(f"\n=== Zusammenfassung ===")
    print(f"Verarbeitet: {total_processed} Rechnung(en)")
    print(f"Fehler:      {total_errors}")


if __name__ == "__main__":
    main()
