# InvoiceFlow - Rechnungen POC

Automatische Verarbeitung von Eingangsrechnungen per E-Mail mit lokalem LLM und Google Workspace APIs.

## Flow

Die Kernlogik bleibt unverändert:

1. Gmail lesen
2. PDF-Text extrahieren
3. Rechnung erkennen
4. Rechnungsfelder extrahieren
5. PDF nach Google Drive hochladen
6. Daten in Google Sheets anhängen

## Projektstruktur

```text
.
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── src/
│   └── rechnungen_poc/
│       ├── cli.py
│       ├── config.py
│       ├── drive.py
│       ├── gmail.py
│       ├── google_auth.py
│       ├── llm.py
│       ├── logging.py
│       ├── models.py
│       ├── pdf.py
│       ├── pipeline.py
│       ├── sheets.py
│       └── utils.py
└── tests/
```

## Voraussetzungen

- Python 3.11+
- Lokales Ollama mit einem verfügbaren Modell
- Google Cloud OAuth Client Credentials
- Zugriff auf Gmail, Google Drive und Google Sheets

## Setup

1. Virtuelle Umgebung erstellen und aktivieren.
2. Abhängigkeiten installieren:

```bash
pip install -r requirements-dev.txt
```

3. `.env.example` nach `.env` kopieren und Werte setzen.
4. `credentials.json` aus der Google Cloud Console im Projekt ablegen.
5. Anwendung starten:

```bash
python main.py
```

Für einen sicheren Durchlauf ohne Schreibzugriffe:

```bash
python main.py --dry-run
```

## Konfiguration

Wichtige `.env`-Variablen:

- `GOOGLE_CREDENTIALS_FILE`
- `GOOGLE_TOKEN_FILE`
- `GMAIL_QUERY`
- `GMAIL_MAX_RESULTS`
- `INCLUDE_PROCESSED_EMAILS`
- `GMAIL_PROCESSED_LABEL`
- `SPREADSHEET_ID`
- `SHEET_NAME`
- `DRIVE_FOLDER_ID`
- `OLLAMA_URL`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT_SECONDS`
- `OLLAMA_NUM_CTX`
- `LOG_LEVEL`

## Tests

```bash
pytest
```

Abgedeckt sind aktuell:

- PDF-Extraktions-Wrapper
- JSON-Extraktion aus LLM-Ausgaben
- Drive-Dateinamen-Sanitizing
- Google-Sheets-Row-Mapping

## Hinweise

- `--dry-run` führt alle Lese-, PDF- und LLM-Schritte aus, überspringt aber Drive-, Sheets- und Gmail-Schreiboperationen.
- Ollama bleibt lokal angebunden, es gibt keine Cloud-LLM-Abhängigkeit.
- Bestehende flache Skriptdateien wurden nicht zwangsweise entfernt, damit laufende lokale Arbeit nicht überschrieben wird. Der neue Einstiegspunkt verwendet ausschließlich die `src/rechnungen_poc`-Struktur.
