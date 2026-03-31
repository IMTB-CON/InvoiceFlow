from dotenv import load_dotenv
load_dotenv()

from gmail_reader import get_google_credentials
from googleapiclient.discovery import build

MESSAGE_IDS = [
    "19d3f2c797014351",
    "19d3f27854f347ea",
]


def walk(part, out):
    mime = part.get("mimeType", "")
    name = part.get("filename", "")
    body = part.get("body", {})
    if name or body.get("attachmentId") or body.get("data"):
        out.append({
            "filename": name,
            "mime": mime,
            "has_attachment_id": bool(body.get("attachmentId")),
            "has_inline_data": bool(body.get("data")),
        })
    for child in part.get("parts", []):
        walk(child, out)


def main():
    creds = get_google_credentials()
    service = build("gmail", "v1", credentials=creds)

    for msg_id in MESSAGE_IDS:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("Subject", "")
        print("MSG", msg_id)
        print("SUBJECT", subject)

        found = []
        walk(msg.get("payload", {}), found)

        pdf_count = 0
        for item in found:
            filename = (item["filename"] or "").lower()
            if item["mime"] == "application/pdf" or filename.endswith(".pdf"):
                pdf_count += 1

        print("PDF_COUNT", pdf_count)
        print("ATTACHMENTS")
        for item in found:
            print(item)
        print("---")


if __name__ == "__main__":
    main()
