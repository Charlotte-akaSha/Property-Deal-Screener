"""Listings marked as contacted or contingent. Stored on this computer, not in Google Sheets."""

from __future__ import annotations

import json

from utils import ROOT

_CONTACTED_PATH = ROOT / ".cache" / "contacted.json"
_CONTINGENT_PATH = ROOT / ".cache" / "contingent.json"


def _load(path) -> set[str]:
    if not path.is_file():
        return set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if isinstance(raw, list):
        return {str(item) for item in raw if str(item).strip()}
    return set()


def _save(path, ids: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(ids), indent=2), encoding="utf-8")


def _toggle(path, property_id: str) -> bool:
    pid = str(property_id).strip()
    ids = _load(path)
    if pid in ids:
        ids.remove(pid)
        _save(path, ids)
        return False
    ids.add(pid)
    _save(path, ids)
    return True


def contacted_ids() -> set[str]:
    return _load(_CONTACTED_PATH)


def toggle_contacted(property_id: str) -> bool:
    """Flip the flag. Returns True when the listing is now contacted."""
    return _toggle(_CONTACTED_PATH, property_id)


def contingent_ids() -> set[str]:
    return _load(_CONTINGENT_PATH)


def toggle_contingent(property_id: str) -> bool:
    """Flip the flag. Returns True when the listing is now contingent."""
    return _toggle(_CONTINGENT_PATH, property_id)
