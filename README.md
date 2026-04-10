# InvoiceFlow

Automated processing of incoming invoices from e-mail — extracts structured data with rule-based regex, uploads PDFs to Google Drive, and writes rows to Google Sheets.

## How it works

1. Fetch e-mails from Gmail that match an invoice query
2. Extract text from PDF attachments
3. Detect whether the PDF is an invoice (skip receipts)
4. Extract fields (vendor, date, amount, currency, description, reference, …) with regex
5. Detect the recipient company (IMTB Consulting GmbH vs IMTB Group GmbH)
6. Upload the PDF to Google Drive with a structured filename
7. Append a row to Google Sheets including a self-calculating `Datei-Benennung` formula
8. Mark the e-mail as processed in Gmail

## Sheet columns

| Column | Description |
|--------|-------------|
| Rechnungsnummer | Auto-generated sequential number (`CON_ER-YYYY-NNNN`) |
| Rg.-Datum | Invoice date (YYYY-MM-DD) |
| Empfänger | Recipient company (IMTB Consulting GmbH / IMTB Group GmbH) — highlighted yellow for IMTB Group |
| Lieferant | Vendor / supplier name |
| Rg.-Grund | Short description of what the invoice is for |
| Summe | Gross amount + currency (e.g. `79.67 EUR`, `20.00 USD`) — highlighted yellow for non-EUR |
| Kostenstelle | Cost centre — filled in manually, dropdown available |
| Status | Payment method — filled in manually, dropdown available (`Überweisung`, `Lastschrift`, `Kreditkarte`, …) |
| Datei-Benennung | Auto-calculated filename formula (`{YEAR}_{SEQ} RG_{YYMMDD}_{Vendor}_{Description}_KS{Kostenstelle}{suffix}`) |
| E-Mail Datum | Date the e-mail was received (YYYY-MM-DD) |
| E-Mail Absender | Sender e-mail address |

## Project structure

```text
.
├── requirements.txt
├── requirements-dev.txt
├── src/
│   └── rechnungen_poc/
│       ├── cli.py          # CLI entry point (--dry-run flag)
│       ├── config.py       # AppConfig loaded from .env
│       ├── drive.py        # Google Drive upload + filename generation
│       ├── gmail.py        # Gmail fetch + mark-as-processed
│       ├── google_auth.py  # OAuth2 flow
│       ├── llm.py          # Regex-based extraction (no LLM required)
│       ├── logging.py      # JSON structured logging
│       ├── models.py       # InvoiceData, EmailMessage, PdfAttachment
│       ├── pdf.py          # PDF text extraction (pypdfium2)
│       ├── pipeline.py     # Orchestration
│       ├── sheets.py       # Google Sheets writer + dropdown validation
│       └── utils.py        # Shared helpers
└── tests/
```

## Prerequisites

- Python 3.11+
- Google Cloud OAuth Client Credentials (Gmail, Drive, Sheets scopes)
- A Google Sheets spreadsheet and Drive folder

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements-dev.txt
```

3. Copy `.env.example` to `.env` and fill in the values.
4. Place `credentials.json` from the Google Cloud Console in the project root.
5. Run the pipeline:

```bash
python -m rechnungen_poc
```

Dry run (read-only — no Drive/Sheets/Gmail writes):

```bash
python -m rechnungen_poc --dry-run
```

## Configuration (`.env`)

| Variable | Description |
|----------|-------------|
| `GOOGLE_CREDENTIALS_FILE` | Path to OAuth credentials JSON |
| `GOOGLE_TOKEN_FILE` | Path where the token is cached |
| `GMAIL_QUERY` | Gmail search query to find invoice e-mails |
| `GMAIL_MAX_RESULTS` | Max e-mails to fetch per run |
| `INCLUDE_PROCESSED_EMAILS` | Also process already-labelled e-mails (`true`/`false`) |
| `SPREADSHEET_ID` | Target Google Sheets ID |
| `SHEET_NAME` | Sheet tab name |
| `DRIVE_FOLDER_ID` | Target Google Drive folder ID |
| `OWN_COMPANY_NAMES` | Comma-separated list of own company names for recipient detection |
| `LOG_LEVEL` | Logging level (`INFO`, `DEBUG`, …) |

## Current limitations / roadmap

- **E-mail source**: currently reads Gmail via personal OAuth. Microsoft 365 / Exchange support is planned.
- **Document storage**: currently uploads to Google Drive. Alfresco DMS integration is planned.

## Tests

```bash
pytest
```
