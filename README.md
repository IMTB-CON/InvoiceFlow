# 🧾 Rechnungen POC – KI-Assistent für Eingangsrechnungen

Automatische Verarbeitung von Eingangsrechnungen per E-Mail mit lokalem LLM.

## Was macht dieses Projekt?

1. Liest E-Mails mit Rechnungsanhängen aus Gmail aus
2. Erkennt automatisch ob ein PDF eine Rechnung ist (mehrsprachig)
3. Extrahiert relevante Daten per lokalem LLM (Ollama / Qwen)
4. Legt die PDF-Datei automatisch in Google Drive ab
5. Trägt die Daten in eine Google Sheets Tabelle ein

Kostenstelle und Status werden anschließend manuell in der Tabelle eingetragen.

## Tech-Stack

- **Python 3.11+** – Skript läuft im Terminal (macOS)
- **Ollama + Qwen** – lokales LLM, keine Cloud-Abhängigkeit
- **Gmail API** – E-Mails und Anhänge abrufen
- **Google Sheets API** – Daten eintragen
- **Google Drive API** – PDFs ablegen
- **pdfplumber** – Text aus PDFs extrahieren
