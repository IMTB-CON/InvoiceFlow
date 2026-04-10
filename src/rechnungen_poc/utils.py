from __future__ import annotations

import re
from decimal import Decimal


def sanitize_drive_component(value: str) -> str:
    normalized = value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    normalized = normalized.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
    normalized = normalized.replace("ß", "ss")
    normalized = re.sub(r"[^\w\-]", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "unbekannt"


def decimal_to_sheet_value(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value, "f")
