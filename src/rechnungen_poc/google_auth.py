from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from rechnungen_poc.config import AppConfig


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def get_google_credentials(config: AppConfig) -> Credentials:
    creds = None
    token_file = Path(config.google_token_file)

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(token_file.as_posix(), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                Path(config.google_credentials_file).as_posix(),
                SCOPES,
            )
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    return creds
