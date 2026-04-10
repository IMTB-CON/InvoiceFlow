from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


TRUTHY_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppConfig:
    google_credentials_file: Path
    google_token_file: Path
    gmail_query: str
    gmail_max_results: int
    include_processed_emails: bool
    processed_label_name: str
    spreadsheet_id: str
    sheet_name: str
    drive_folder_id: str
    ollama_url: str
    ollama_model: str
    ollama_timeout_seconds: int
    ollama_num_ctx: int
    log_level: str
    own_company_names: frozenset[str] = frozenset()
    dry_run: bool = False

    @classmethod
    def load(cls, dry_run: bool = False) -> "AppConfig":
        load_dotenv()
        config = cls(
            google_credentials_file=Path(_get_env("GOOGLE_CREDENTIALS_FILE", default="credentials.json")),
            google_token_file=Path(_get_env("GOOGLE_TOKEN_FILE", default="token.json")),
            gmail_query=_get_env(
                "GMAIL_QUERY",
                default=(
                    "subject:(Rechnung OR Invoice OR Fatura OR Factura OR Fattura OR Faktura OR "
                    "Счёт) has:attachment newer_than:30d"
                ),
            ),
            gmail_max_results=_get_int_env("GMAIL_MAX_RESULTS", default=10, minimum=1),
            include_processed_emails=_get_bool_env("INCLUDE_PROCESSED_EMAILS", default=False),
            processed_label_name=_get_env("GMAIL_PROCESSED_LABEL", default="Verarbeitet"),
            spreadsheet_id=_get_env("SPREADSHEET_ID"),
            sheet_name=_get_env("SHEET_NAME", default="Eingangsrechnungen"),
            drive_folder_id=_get_env("DRIVE_FOLDER_ID"),
            ollama_url=_get_env("OLLAMA_URL", default="http://localhost:11434/api/generate"),
            ollama_model=_get_env("OLLAMA_MODEL", default="qwen3.5:27b-128k"),
            ollama_timeout_seconds=_get_int_env("OLLAMA_TIMEOUT_SECONDS", default=180, minimum=1),
            ollama_num_ctx=_get_int_env("OLLAMA_NUM_CTX", default=131072, minimum=1024),
            log_level=_get_env("LOG_LEVEL", default="INFO").upper(),
            own_company_names=_get_frozenset_env("OWN_COMPANY_NAMES"),
            dry_run=dry_run,
        )
        config.validate()
        return config

    def validate(self) -> None:
        missing: list[str] = []
        if not self.google_credentials_file.as_posix().strip():
            missing.append("GOOGLE_CREDENTIALS_FILE")
        if not self.google_token_file.as_posix().strip():
            missing.append("GOOGLE_TOKEN_FILE")
        if not self.dry_run:
            if not self.sheet_name.strip():
                missing.append("SHEET_NAME")
            if not self.spreadsheet_id.strip():
                missing.append("SPREADSHEET_ID")
            if not self.drive_folder_id.strip():
                missing.append("DRIVE_FOLDER_ID")
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required configuration values: {joined}")


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


def _get_frozenset_env(name: str) -> frozenset[str]:
    value = os.getenv(name)
    if not value or not value.strip():
        return frozenset()
    return frozenset(entry.strip() for entry in value.split(",") if entry.strip())


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUTHY_VALUES


def _get_int_env(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer.") from exc
    if value < minimum:
        raise ValueError(f"Environment variable {name} must be >= {minimum}.")
    return value
