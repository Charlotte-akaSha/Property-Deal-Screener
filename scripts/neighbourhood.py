"""Infer Columbus submarket / neighbourhood labels for Sheet and Compare."""

from __future__ import annotations

import re

_GENERIC = frozenset(
    {"columbus", "columbus oh", "columbus, oh", "ohio", "oh", "nan", "none", ""}
)

# Approximate submarkets for Columbus mailing-city zips (investor-facing labels).
_COLUMBUS_ZIP_HINTS: dict[str, str] = {
    "43201": "University District",
    "43202": "Clintonville",
    "43203": "King-Lincoln Bronzeville",
    "43204": "Hilltop",
    "43205": "Driving Park",
    "43206": "German Village",
    "43207": "South Columbus",
    "43209": "Bexley",
    "43211": "Northeast Columbus",
    "43212": "Westgate",
    "43213": "Whitehall",
    "43214": "Clintonville",
    "43215": "Downtown",
    "43219": "Northeast Columbus",
    "43220": "Upper Arlington",
    "43221": "Upper Arlington",
    "43222": "Franklinton",
    "43223": "Hilltop",
    "43224": "Northland",
    "43227": "East Columbus",
    "43228": "West Columbus",
    "43229": "Northland",
    "43230": "Gahanna",
    "43231": "Northeast Columbus",
    "43232": "Southeast Columbus",
    "43235": "Dublin",
}


def _clean(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip())


def _is_generic(name: str) -> bool:
    return _clean(name).lower() in _GENERIC


def zip_from_listing_url(url: object) -> str:
    raw = str(url or "")
    match = re.search(r"OH-(\d{5})/", raw, re.IGNORECASE)
    return match.group(1) if match else ""


def infer_from_research(text: object) -> str:
    """Pull a neighbourhood name from market-research prose when the short field is empty."""
    body = str(text or "").strip()
    if not body:
        return ""
    patterns = (
        r"located in ([^.,\n]+)",
        r"in the ([^.,\n]+?) (?:neighborhood|neighbourhood|area)\b",
        r"in ([A-Z][^.,\n]{2,60}?), a (?:historic|vibrant|growing)",
        r"neighbourhood_name[\"']?\s*:\s*[\"']([^\"']+)",
    )
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if not match:
            continue
        candidate = _clean(match.group(1))
        if candidate and not _is_generic(candidate):
            return candidate
    return ""


def infer_from_zip(zip_code: object, city: object) -> str:
    city_s = str(city or "").strip().lower()
    if city_s not in ("columbus", ""):
        return ""
    z = str(zip_code or "").strip()[:5]
    if len(z) != 5:
        return ""
    return _COLUMBUS_ZIP_HINTS.get(z, "")


def resolve_neighbourhood_name(
    *,
    neighbourhood_name: object = None,
    neighbourhood_research: object = None,
    city: object = None,
    state: object = None,
    zip_code: object = None,
    listing_url: object = None,
) -> str:
    """
    Best label for Neighbourhood column / Compare.

    Order: model short name → research prose → Columbus zip hint → (not city alone).
    """
    direct = _clean(str(neighbourhood_name or ""))
    if direct and not _is_generic(direct):
        return direct

    from_research = infer_from_research(neighbourhood_research)
    if from_research:
        return from_research

    z = str(zip_code or "").strip()[:5] or zip_from_listing_url(listing_url)
    from_zip = infer_from_zip(z, city)
    if from_zip:
        return from_zip

    return direct


def neighbourhood_display_label(
    neighbourhood: object = None,
    city: object = None,
    state: object = None,
    *,
    neighbourhood_research: object = None,
    zip_code: object = None,
    listing_url: object = None,
) -> str:
    """Area label for Compare — inferred submarket, not mailing city alone."""
    resolved = resolve_neighbourhood_name(
        neighbourhood_name=neighbourhood,
        neighbourhood_research=neighbourhood_research,
        city=city,
        state=state,
        zip_code=zip_code,
        listing_url=listing_url,
    )
    if resolved and not _is_generic(resolved):
        return resolved
    city_s = str(city or "").strip()
    state_s = str(state or "").strip()
    if city_s and not _is_generic(city_s):
        return f"{city_s}, {state_s}".strip(" ,") if state_s else city_s
    if city_s or state_s:
        return f"{city_s}, {state_s}".strip(" ,")
    return "—"
