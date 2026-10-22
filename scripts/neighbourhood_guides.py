"""Long-form neighbourhood investment guides for Compare / Visits popups."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from utils import ROOT

_SECTION_KEYS: tuple[tuple[str, str], ...] = (
    ("Rental", "rental"),
    ("Appreciation", "appreciation"),
    ("Flood", "flood"),
    ("Future improvements", "future_improvements"),
    ("Investment view", "investment_view"),
)

_GUIDE_FILE = ROOT / "data" / "neighbourhood_investment_guides.txt"
_JSON_CACHE = ROOT / "data" / "neighbourhood_guides.json"


def _norm(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _parse_guide_block(block: str) -> dict[str, Any] | None:
    lines = block.strip().split("\n", 1)
    if not lines or "Rental:" not in block:
        return None
    title = lines[0].strip()
    body = lines[1] if len(lines) > 1 else ""
    sections: dict[str, str] = {}
    for i, (heading, key) in enumerate(_SECTION_KEYS):
        marker = f"{heading}:"
        start = body.find(marker)
        if start < 0:
            continue
        start += len(marker)
        end = len(body)
        for next_heading, _ in _SECTION_KEYS[i + 1 :]:
            idx = body.find(f"\n{next_heading}:", start)
            if idx >= 0:
                end = idx
                break
        sections[key] = body[start:end].strip()
    if not title or not sections:
        return None
    return {"title": title, **sections}


@lru_cache(maxsize=1)
def _guides_index() -> list[tuple[str, dict[str, Any]]]:
    if _JSON_CACHE.is_file():
        raw = json.loads(_JSON_CACHE.read_text(encoding="utf-8"))
        items = [(k, v) for k, v in raw.items()]
        return sorted(items, key=lambda item: -len(item[0]))

    if not _GUIDE_FILE.is_file():
        return []

    text = _GUIDE_FILE.read_text(encoding="utf-8")
    blocks = re.split(r"\n\n+(?=[^\n]+\nRental:)", text.strip())
    guides: dict[str, dict[str, Any]] = {}
    for block in blocks:
        parsed = _parse_guide_block(block)
        if not parsed:
            continue
        needle = _norm(parsed["title"])
        guides[needle] = parsed

    _JSON_CACHE.write_text(json.dumps(guides, indent=2), encoding="utf-8")
    return sorted(guides.items(), key=lambda item: -len(item[0]))


def neighbourhood_investment_guide(label: object) -> dict[str, Any] | None:
    hay = _norm(label)
    if not hay:
        return None
    for needle, guide in _guides_index():
        if needle in hay or hay in needle:
            return guide
    from neighbourhood_tiers import _PROFILES

    for _tier, profile_needle, _a, _r in _PROFILES:
        if profile_needle in hay:
            for needle, guide in _guides_index():
                if profile_needle in needle or needle in profile_needle:
                    return guide
    return None


def format_investment_guide_markdown(guide: dict[str, Any]) -> str:
    title = str(guide.get("title") or "Neighbourhood")
    parts = [f"### {title}"]
    for heading, key in _SECTION_KEYS:
        text = str(guide.get(key) or "").strip()
        if text:
            parts.append(f"**{heading}:** {text}")
    return "\n\n".join(parts)
