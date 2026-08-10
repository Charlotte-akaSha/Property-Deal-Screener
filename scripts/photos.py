"""Locate and thumbnail the screenshots archived with each property."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from utils import ROOT

PHOTO_GLOBS = ("photo*.png", "photo*.jpg", "photo*.jpeg", "photo*.webp", "photo*.gif")
STATIC_THUMBS = ROOT / "static" / "property_thumbs"
PLACEHOLDER_SVG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='160' height='120'>"
    "<rect width='100%' height='100%' rx='16' fill='%23E7EBF7'/>"
    "<text x='50%' y='52%' text-anchor='middle' fill='%238891AF' "
    "font-family='sans-serif' font-size='14'>No photo</text></svg>"
)


def find_property_photo(property_id: str) -> Path | None:
    folder = ROOT / "properties" / str(property_id)
    if not folder.is_dir():
        return None
    for pattern in PHOTO_GLOBS:
        matches = sorted(folder.glob(pattern))
        if matches:
            return matches[0]
    return None


def ensure_thumbnail(property_id: str, *, max_side: int = 240) -> Path | None:
    """Write a JPEG thumbnail under static/ and return its path."""
    source = find_property_photo(property_id)
    if source is None:
        return None

    STATIC_THUMBS.mkdir(parents=True, exist_ok=True)
    dest = STATIC_THUMBS / f"{property_id}.jpg"
    try:
        if dest.exists() and dest.stat().st_mtime_ns >= source.stat().st_mtime_ns:
            return dest
        with Image.open(source) as img:
            rgb = img.convert("RGB")
            rgb.thumbnail((max_side, max_side))
            rgb.save(dest, format="JPEG", quality=78, optimize=True)
        return dest
    except OSError:
        return None


def photo_url_for(property_id: str) -> str:
    """URL Streamlit ImageColumn can fetch (static serving or SVG placeholder)."""
    thumb = ensure_thumbnail(str(property_id))
    if thumb is None:
        return PLACEHOLDER_SVG
    # Leading slash is required so the dataframe frontend treats this as a URL,
    # not plain text.
    return f"/app/static/property_thumbs/{thumb.name}"


def readable_property_name(property_id: object) -> str:
    return str(property_id or "").replace("_", " ").strip()
