"""Resolve property coordinates for the map, cached on disk to limit Maps API calls."""

from __future__ import annotations

import json

from transit_lookup import format_property_address, geocode_address
from utils import ROOT

CACHE_PATH = ROOT / ".cache" / "geocode.json"


def _load_cache() -> dict[str, list[float]]:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict[str, list[float]]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def address_for(property_id: str) -> str:
    """Best known address: the archived analysis if present, else the ID slug."""
    latest = ROOT / "properties" / property_id / "latest.json"
    if latest.exists():
        try:
            extracted = json.loads(latest.read_text(encoding="utf-8")).get("extracted", {})
            address = format_property_address(extracted).strip()
            if address:
                return address
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
    return property_id.replace("_", " ")


def coordinates_for(property_ids: list[str]) -> dict[str, tuple[float, float]]:
    """Map Property ID to (lat, lon). Only geocodes IDs missing from the cache."""
    cache = _load_cache()
    added = False
    for pid in property_ids:
        if pid in cache:
            continue
        try:
            lat, lon = geocode_address(address_for(pid))
        except Exception:  # noqa: BLE001 — a failed lookup just leaves the pin off the map
            continue
        cache[pid] = [lat, lon]
        added = True
    if added:
        _save_cache(cache)
    return {
        pid: (float(cache[pid][0]), float(cache[pid][1]))
        for pid in property_ids
        if cache.get(pid)
    }
