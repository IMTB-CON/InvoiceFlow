from dotenv import load_dotenv
load_dotenv()

from gmail_reader import get_google_credentials
from googleapiclient.discovery import build

MESSAGE_IDS = [
    "19d3f2c797014351",
    "19d3f27854f347ea",
]


def main():
    creds = get_google_credentials()
    service = build("gmail", "v1", credentials=creds)

    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    processed_id = ""
    for label in labels:
        if label.get("name") == "Verarbeitet":
            processed_id = label.get("id", "")
            break

    if not processed_id:
        print("Kein Label 'Verarbeitet' gefunden.")
        return

    for message_id in MESSAGE_IDS:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": [processed_id]},
        ).execute()
        print(f"Label entfernt: {message_id}")


if __name__ == "__main__":
    main()
