from dotenv import load_dotenv
load_dotenv()

from gmail_reader import get_google_credentials
from googleapiclient.discovery import build


def main():
    creds = get_google_credentials()
    service = build("gmail", "v1", credentials=creds)

    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    processed_id = ""
    for label in labels:
        if label.get("name") == "Verarbeitet":
            processed_id = label.get("id", "")
            break

    res = service.users().messages().list(
        userId="me",
        q="has:attachment newer_than:365d",
        maxResults=10,
    ).execute()
    msgs = res.get("messages", [])

    print("TOTAL_ATTACHMENTS_QUERY", len(msgs))
    print("PROCESSED_LABEL_ID", processed_id or "-")

    for msg in msgs:
        full = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["Subject", "From"],
        ).execute()
        headers = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
        label_ids = set(full.get("labelIds", []))
        state = "PROCESSED" if processed_id and processed_id in label_ids else "UNPROCESSED"
        print("MSG", msg["id"], state, "SUBJECT", headers.get("Subject", "")[:90])


if __name__ == "__main__":
    main()
