# KI-Assistent: Eingangsrechnungen – POC

## Projektübersicht

Automatische Verarbeitung von Eingangsrechnungen per E-Mail:
1. Gmail-Postfach auslesen (`jonatas.langdock@gmail.com`)
2. Anhänge (PDFs) herunterladen und Text extrahieren
3. Rechnungsdaten per Ollama/Qwen extrahieren
4. Human-in-the-Loop: Prüfen, Kostenstelle ergänzen, bestätigen
5. Bestätigte Daten in Google Sheets eintragen

**Produktiv-Ziel (nach POC):** Outlook + Alfresco statt Gmail + Google Sheets.

---

## Tech-Stack

| Komponente | Technologie |
|---|---|
| Sprache | Python 3.11+ |
| UI (Human-in-the-Loop) | Streamlit |
| E-Mail | Gmail API (Google OAuth2) |
| LLM | Ollama lokal mit Qwen (z.B. `qwen2.5:7b`) |
| PDF-Extraktion | pdfplumber |
| Tabelle (lokal) | Google Sheets API |
| Tabelle (produktiv) | Alfresco |

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
├── app.py                     # Streamlit-Einstiegspunkt
│
├── gmail_reader.py            # Gmail API: E-Mails + Anhänge abrufen
├── pdf_extractor.py           # PDF-Text per pdfplumber extrahieren
├── llm_extractor.py           # Ollama/Qwen: Rechnungsdaten extrahieren
└── sheets_writer.py           # Google Sheets API: Daten eintragen
```

---

## Module – Beschreibung & Anforderungen

### `gmail_reader.py`
- Google OAuth2 mit Scopes: `gmail.readonly` + `spreadsheets`
- Funktion `fetch_invoice_emails(creds, max_results)`:
  - Gmail-Query: `subject:(Rechnung OR Invoice) has:attachment newer_than:30d`
  - Für jede E-Mail zurückgeben: `id`, `subject`, `sender`, `date`, `body` (plain text), `pdfs` (Liste von `{name, bytes}`)
  - PDF-Anhänge als Bytes über die Attachments-API herunterladen
- Funktion `get_google_credentials()`:
  - Token aus `token.json` lesen, bei Ablauf refreshen
  - Falls kein Token: OAuth2-Flow mit `credentials.json` starten, Token speichern

### `pdf_extractor.py`
- Funktion `extract_pdf_text(pdf_bytes: bytes) -> str`:
  - PDF temporär auf Disk schreiben, mit pdfplumber öffnen
  - Text aller Seiten zusammenführen, temporäre Datei löschen
  - Rückgabe: reiner Text-String

### `llm_extractor.py`
- Ollama-Endpunkt: `http://localhost:11434/api/generate`
- Modell: konfigurierbar per `.env`, Standard `qwen2.5:7b`
- Funktion `extract_invoice_data(text: str) -> dict`:
  - Text auf max. 4000 Zeichen kürzen
  - Prompt sendet den Text und fordert **ausschließlich JSON** zurück
  - JSON per Regex aus der Antwort extrahieren und parsen
  - Felder die extrahiert werden sollen:
    - `rechnungssteller` – Name des Rechnungsstellers
    - `rechnungsnummer` – Rechnungs- oder Belegnummer
    - `rechnungsdatum` – Datum im Format TT.MM.JJJJ
    - `betrag_netto` – Nettobetrag als Zahl (z.B. `1234.56`)
    - `betrag_brutto` – Bruttobetrag als Zahl
    - `mwst_satz` – MwSt-Satz als Zahl (z.B. `19`)
    - `waehrung` – Währungskürzel, meist `EUR`
    - `beschreibung` – Kurzbeschreibung der Leistung, max. 100 Zeichen
  - Bei nicht gefundenem Feld: `null` setzen
  - Bei Fehler: leeres dict `{}` zurückgeben und Fehler loggen

### `sheets_writer.py`
- Spreadsheet-ID und Sheet-Name aus `.env` lesen
- Funktion `ensure_header(service, spreadsheet_id)`:
  - Prüfen ob Zeile A1 bereits Spaltenüberschriften enthält
  - Falls nicht: Header-Zeile anlegen
  - Spalten: `Rechnungssteller | Rechnungsnummer | Rechnungsdatum | Betrag Netto (EUR) | Betrag Brutto (EUR) | MwSt % | Währung | Beschreibung | Kostenstelle | Bestätigt | E-Mail Datum | E-Mail Absender`
- Funktion `append_to_sheet(creds, extracted_data, email_meta, kostenstelle)`:
  - Neue Zeile am Ende der Tabelle anhängen
  - `Bestätigt` auf `Ja` setzen (wird nur nach menschlicher Bestätigung aufgerufen)

### `app.py` – Streamlit UI
Die App hat drei Bereiche:

**Bereich 1 – E-Mails laden**
- Button „Gmail laden" → ruft `fetch_invoice_emails` auf
- Ergebnis in `st.session_state` speichern
- Anzeige: Anzahl gefundener E-Mails

**Bereich 2 – Verarbeitung je E-Mail**
- Jede E-Mail als aufklappbarer `st.expander`
- PDF-Text extrahieren und an Ollama senden
- Extrahierte Felder als editierbare Formularfelder anzeigen (`st.text_input`)
- Zusatzfeld: `Kostenstelle` (manuell einzutragen)
- Button „✅ Bestätigen & in Sheets eintragen" → ruft `append_to_sheet` auf
- Nach Eintrag: Erfolgsanzeige, E-Mail aus der Liste entfernen

**Bereich 3 – Status**
- Anzeige wie viele Rechnungen bereits eingetragen wurden (in dieser Session)
- Link zur Google Sheets Tabelle

---

## Umgebungsvariablen (`.env`)

```env
# Ollama
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=qwen2.5:7b

# Google Sheets
SPREADSHEET_ID=HIER_DEINE_SPREADSHEET_ID
SHEET_NAME=Eingangsrechnungen

# Gmail
GMAIL_QUERY=subject:(Rechnung OR Invoice) has:attachment newer_than:30d
GMAIL_MAX_RESULTS=10
```

---

## `requirements.txt`

```
streamlit
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

## Setup-Schritte

### 1. Google Cloud Projekt einrichten
1. [console.cloud.google.com](https://console.cloud.google.com) öffnen
2. Neues Projekt erstellen (z.B. `rechnungen-poc`)
3. APIs aktivieren: **Gmail API** + **Google Sheets API**
4. OAuth2-Credentials erstellen (Typ: Desktop App)
5. `credentials.json` herunterladen → in den Projektordner legen

### 2. Google Sheets Tabelle vorbereiten
1. Die Tabelle unter dem folgenden Link öffnen:
   `https://drive.google.com/drive/u/3/folders/1U_iN2zVDecjmKWptEVlw_GkjVw0DZPzo`
2. Spreadsheet-ID aus der URL kopieren
3. In `.env` unter `SPREADSHEET_ID` eintragen
4. Sicherstellen dass ein Sheet namens `Eingangsrechnungen` existiert

### 3. Ollama einrichten
```bash
# Modell herunterladen (falls noch nicht vorhanden)
ollama pull qwen2.5:7b

# Ollama starten (läuft im Hintergrund)
ollama serve
```

### 4. Python-Umgebung einrichten
```bash
python -m venv .venv
source .venv/bin/activate      # Mac/Linux
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 5. App starten
```bash
streamlit run app.py
```
Beim ersten Start öffnet sich der Google OAuth2-Browser-Flow zur Authentifizierung.

---

## Spätere Produktiv-Migration

| Komponente | POC | Produktiv |
|---|---|---|
| E-Mail | Gmail API | Microsoft Graph API (Outlook) |
| Tabelle | Google Sheets API | Alfresco REST API |
| Auth | Google OAuth2 | Microsoft OAuth2 / Alfresco Basic Auth |
| LLM | Ollama lokal | Ollama lokal oder Cloud-Modell |

Die Module `gmail_reader.py` und `sheets_writer.py` werden durch `outlook_reader.py` und `alfresco_writer.py` ersetzt – der Rest der App bleibt unverändert.
