from dotenv import load_dotenv
load_dotenv()

import os
from gmail_reader import get_google_credentials, fetch_invoice_emails


def main():
    print("ENV_QUERY", os.getenv("GMAIL_QUERY"))
    creds = get_google_credentials()
    emails = fetch_invoice_emails(creds, max_results=20)
    print("FETCH_COUNT", len(emails))
    for email in emails:
        print("EMAIL", email.get("id"), email.get("subject"))
        print("PDFS", [p.get("name") for p in email.get("pdfs", [])])


if __name__ == "__main__":
    main()
