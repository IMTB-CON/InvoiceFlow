# KI-Assistent: Eingangsrechnungen – POC

## Projektübersicht

Automatische Verarbeitung von Eingangsrechnungen per E-Mail:
1. Gmail-Postfach auslesen (`jonatas.langdock@gmail.com`)
2. Anhänge (PDFs) herunterladen und Text extrahieren
3. Rechnungsdaten per Ollama/Qwen extrahieren
4. Extrahierte Daten direkt in Google Sheets eintragen
5. PDF-Anhang in Google Drive ablegen
6. Kostenstelle und Status werden manuell direkt in der Tabelle eingetragen

Kein UI, kein Human-in-the-Loop. Die App läuft als Python-Skript im Terminal (macOS).

---

## Tech-Stack

| Komponente | Technologie |
|---|---|
| Sprache | Python 3.11+ |
| Laufzeit | Terminal (macOS) |
| E-Mail | Gmail API (Google OAuth2) |
| LLM | Ollama lokal mit Qwen (z.B. `qwen2.5:7b`) |
| PDF-Extraktion | pdfplumber |
| Tabelle | Google Sheets API |
| Dateiablage | Google Drive API |

---

## Projektstruktur

```
rechnungen-poc/
├── CLAUDE.md                  # Diese Datei
├── README.md
├── .env                       # Secrets (nicht ins Git!)
├── .gitignore
├── requirements.txt
├── credentials.json           # Google OAuth2 Client (nicht ins Git!)
├── token.json                 # Wird automatisch generiert (nicht ins Git!)
│
├── main.py                    # Einstiegspunkt – orchestriert alle Module
├── gmail_reader.py            # Gmail API: E-Mails + Anhänge abrufen
├── pdf_extractor.py           # PDF-Text per pdfplumber extrahieren
├── llm_extractor.py           # Ollama/Qwen: Rechnungsdaten extrahieren
├── sheets_writer.py           # Google Sheets API: Daten eintragen
└── drive_uploader.py          # Google Drive API: PDF ablegen
```

---

## Module – Beschreibung & Anforderungen

### `gmail_reader.py`
- Google OAuth2 mit Scopes:
  - `https://www.googleapis.com/auth/gmail.readonly`
  - `https://www.googleapis.com/auth/spreadsheets`
  - `https://www.googleapis.com/auth/drive.file`
- Funktion `get_google_credentials()`:
  - Token aus `token.json` lesen, bei Ablauf refreshen
  - Falls kein Token: OAuth2-Flow mit `credentials.json` starten, Token speichern
- Funktion `fetch_invoice_emails(creds, max_results) -> list[dict]`:
  - Gmail-Query: `subject:(Rechnung OR Invoice OR Fatura OR Factura OR Fattura OR Faktura OR Счёт) has:attachment newer_than:30d`
  - Für jede E-Mail zurückgeben: `id`, `subject`, `sender`, `date`, `body` (plain text), `pdfs` (Liste von `{name, bytes}`)
  - Nur E-Mails die noch nicht verarbeitet wurden (Label-Check, siehe unten)
- Funktion `mark_as_processed(creds, message_id)`:
  - Gmail-Label `Verarbeitet` anlegen falls nicht vorhanden
  - Label auf die E-Mail setzen, damit sie beim nächsten Lauf übersprungen wird

### `pdf_extractor.py`
- Funktion `extract_pdf_text(pdf_bytes: bytes) -> str`:
  - PDF temporär auf Disk schreiben, mit pdfplumber öffnen
  - Text aller Seiten zusammenführen, temporäre Datei löschen
  - Rückgabe: reiner Text-String

### `llm_extractor.py`
- Ollama-Endpunkt: `http://localhost:11434/api/generate`
- Modell: konfigurierbar per `.env`, Standard `qwen2.5:7b`
- Funktion `is_invoice(text: str) -> bool`:
  - Erster LLM-Aufruf: prüft ob der Text eine Rechnung ist – unabhängig von der Sprache
  - Erkennt Rechnungen in allen Sprachen: Rechnung (DE), Invoice (EN), Fatura (PT), Factura (ES), Fattura (IT), Faktura (PL/SE), Счёт (RU) u.a.
  - Prompt fragt nur: ist dies eine Rechnung? Antwort: nur `true` oder `false`
  - Dokumente wie Lieferscheine, Angebote, AGB, Auftragsbestätigungen → `false`
  - Bei Unsicherheit → `true` (lieber zu viel als zu wenig verarbeiten)
  - Wird vor `extract_invoice_data` aufgerufen – nur wenn `true`, wird extrahiert
- Funktion `extract_invoice_data(text: str) -> dict`:
  - Text auf max. 4000 Zeichen kürzen
  - Prompt fordert **ausschließlich JSON** zurück, keine Erklärung
  - JSON per Regex aus der Antwort extrahieren und parsen
  - Felder die extrahiert werden sollen (sprachunabhängig):
    - `rechnungsnummer` – Rechnungs- oder Belegnummer
    - `rechnungsdatum` – Datum im Format TT.MM.JJJJ
    - `lieferant` – Name des Rechnungsstellers / Lieferanten
    - `rechnungsgrund` – Kurzbeschreibung der Leistung, max. 100 Zeichen
    - `summe` – Gesamtbetrag (Brutto) als Zahl (z.B. `1234.56`)
  - Bei nicht gefundenem Feld: `null` setzen
  - Bei Fehler: leeres dict `{}` zurückgeben und Fehler im Terminal ausgeben

### `sheets_writer.py`
- Spreadsheet-ID und Sheet-Name aus `.env` lesen
- Funktion `ensure_header(service, spreadsheet_id)`:
  - Prüfen ob Zeile A1 bereits Spaltenüberschriften enthält
  - Falls nicht: Header-Zeile anlegen
  - Spalten: `Rechnungsnummer | Rg.-Datum | Lieferant | Rg.-Grund | Summe (EUR) | Kostenstelle | Status | Drive-Link | E-Mail Datum | E-Mail Absender`
  - `Kostenstelle` und `Status` bleiben leer – werden manuell eingetragen
- Funktion `append_to_sheet(creds, extracted_data, email_meta, drive_link) -> int`:
  - Neue Zeile am Ende der Tabelle anhängen
  - `drive_link`: direkter Link zur PDF-Datei in Google Drive
  - `Kostenstelle` und `Status` als leere Strings eintragen
  - Automatisch befüllt: `Rechnungsnummer`, `Rg.-Datum`, `Lieferant`, `Rg.-Grund`, `Summe`

### `drive_uploader.py`
- Google Drive Ordner-ID aus `.env` lesen (`DRIVE_FOLDER_ID`)
- Funktion `upload_pdf(creds, pdf_bytes, filename, extracted_data) -> str`:
  - PDF in den konfigurierten Drive-Ordner hochladen
  - Datei-Benennung automatisch nach Schema: `JJJJMMTT_{Lieferant}_{Rechnungsnummer}.pdf`
    - Beispiel: `20240315_MusterGmbH_RE2024-042.pdf`
    - Sonderzeichen, Leerzeichen und Umlaute werden bereinigt (z.B. `ä→ae`, `ö→oe`, `ü→ue`, Leerzeichen→`_`)
    - Falls ein Feld fehlt: Platzhalter `unbekannt` verwenden
  - Rückgabe: direkter `webViewLink` zur Datei in Google Drive

### `main.py`
- Lädt alle Module und orchestriert den Ablauf
- Ablauf für jede E-Mail:
  1. E-Mails per `fetch_invoice_emails` laden
  2. Für jeden PDF-Anhang:
     - Text per `extract_pdf_text` extrahieren
     - Per `is_invoice` prüfen ob es eine Rechnung ist
     - Wenn **nein**: PDF überspringen, im Terminal loggen (`[SKIP] Kein Rechnungsdokument: dateiname.pdf`)
     - Wenn **ja**: Weiter mit Schritt 3
  3. Rechnungsdaten per `extract_invoice_data` extrahieren
  4. PDF per `upload_pdf` in Google Drive ablegen
  5. Extrahierte Daten + Drive-Link per `append_to_sheet` eintragen
  6. Nach allen PDFs der E-Mail: E-Mail per `mark_as_processed` als verarbeitet markieren
  7. Fortschritt im Terminal ausgeben (E-Mail-Betreff, je PDF: extrahierte Felder oder SKIP-Grund)
- Am Ende: Zusammenfassung ausgeben (x E-Mails verarbeitet, x Fehler)
- Fehlerbehandlung: Bei Fehler einer E-Mail trotzdem mit der nächsten weitermachen, Fehler loggen

---

## Umgebungsvariablen (`.env`)

```env
# Ollama
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=qwen2.5:7b

# Google Sheets
SPREADSHEET_ID=HIER_DEINE_SPREADSHEET_ID
SHEET_NAME=Eingangsrechnungen

# Google Drive
DRIVE_FOLDER_ID=1U_iN2zVDecjmKWptEVlw_GkjVw0DZPzo

# Gmail
GMAIL_QUERY=subject:(Rechnung OR Invoice) has:attachment newer_than:30d
GMAIL_MAX_RESULTS=10
```

---

## `requirements.txt`

```
google-auth
google-auth-oauthlib
google-api-python-client
pdfplumber
requests
python-dotenv
```

---

## `.gitignore`

```
.env
credentials.json
token.json
__pycache__/
*.pyc
.venv/
```

---

## Setup-Schritte (macOS)

### 1. Repo klonen und Umgebung einrichten
```bash
git clone https://github.com/DEIN-USERNAME/rechnungen-poc.git
cd rechnungen-poc

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. `credentials.json` ablegen
- Neue `credentials.json` von Google Cloud herunterladen (nach Secret-Reset)
- In den Projektordner legen (neben `main.py`)

### 3. `.env` anlegen
```bash
cp .env.example .env
# Dann SPREADSHEET_ID eintragen
```

### 4. Google Sheets Tabelle vorbereiten
- Tabelle öffnen: `https://drive.google.com/drive/u/3/folders/1U_iN2zVDecjmKWptEVlw_GkjVw0DZPzo`
- Spreadsheet-ID aus der URL kopieren → in `.env` eintragen
- Sheet muss `Eingangsrechnungen` heißen (wird automatisch mit Header befüllt)

### 5. Ollama + Qwen starten
```bash
ollama pull qwen2.5:7b
ollama serve
```

### 6. Skript ausführen
```bash
source .venv/bin/activate
python main.py
```
Beim ersten Start öffnet sich automatisch der Browser für den Google OAuth2-Login.

---

## Produktiv-Migration (nach POC)

| Komponente | POC | Produktiv |
|---|---|---|
| E-Mail | Gmail API | Microsoft Graph API (Outlook) |
| Tabelle | Google Sheets API | Alfresco REST API |
| Dateiablage | Google Drive API | Alfresco Dokumentenmanagement |
| Auth | Google OAuth2 | Microsoft OAuth2 / Alfresco Basic Auth |
| LLM | Ollama lokal | Ollama lokal oder Cloud-Modell |

Die Module `gmail_reader.py`, `sheets_writer.py` und `drive_uploader.py` werden durch ihre Produktiv-Äquivalente ersetzt – `main.py`, `pdf_extractor.py` und `llm_extractor.py` bleiben unverändert.
