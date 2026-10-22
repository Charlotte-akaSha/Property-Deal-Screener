"""Per-property listing contact phones for visit planning (local cache, not on Sheet)."""

from __future__ import annotations

import json
import re
from typing import Any

from utils import ROOT

CACHE_PATH = ROOT / ".cache" / "visit_contacts.json"


def _load_all() -> dict[str, dict[str, str]]:
    if not CACHE_PATH.is_file():
        return {}
    try:
        raw = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for pid, entry in raw.items():
        if isinstance(entry, dict):
            out[str(pid)] = {str(k): str(v) for k, v in entry.items()}
    return out


def _save_all(data: dict[str, dict[str, str]]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def get_contact(property_id: str) -> dict[str, str]:
    return dict(_load_all().get(property_id, {}))


def set_contact(property_id: str, *, phone: str | None = None, agent_name: str | None = None) -> None:
    data = _load_all()
    row = dict(data.get(property_id, {}))
    if phone is not None:
        row["phone"] = phone.strip()
    if agent_name is not None:
        row["agent_name"] = agent_name.strip()
    data[property_id] = row
    _save_all(data)


def digits_only(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def whatsapp_number(phone: str, default_country: str = "1") -> str:
    """E.164 digits only (no +) for wa.me links. Assumes US/Canada if 10 digits."""
    d = digits_only(phone)
    if not d:
        return ""
    if len(d) == 10 and default_country:
        return f"{default_country}{d}"
    if len(d) == 11 and d.startswith("1"):
        return d
    return d


def whatsapp_href(phone: str, message: str, default_country: str = "1") -> str:
    from urllib.parse import quote

    num = whatsapp_number(phone, default_country=default_country)
    if not num:
        return ""
    text = quote(message, safe="")
    return f"https://wa.me/{num}?text={text}"
