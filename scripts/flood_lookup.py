"""FEMA NFHL + Columbus heuristics for flood exposure (supplements LLM scores)."""

from __future__ import annotations

import json
import re
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass

import certifi

from neighbourhood import neighbourhood_display_label
from utils import ROOT

FEMA_NFHL_QUERY = (
    "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
)
_CACHE_PATH = ROOT / ".cache" / "fema_flood.json"

_HIGH_ZONES = frozenset({"A", "AE", "AH", "AO", "AR", "A99", "V", "VE"})

_HIGH_RISK_PATTERNS: tuple[str, ...] = (
    "franklinton",
    "west franklinton",
    "scioto peninsula",
    "brewery district",
    "harrison west",
)

_MODERATE_RISK_PATTERNS: tuple[str, ...] = (
    "milo-grogan",
    "king-lincoln",
    "bronzeville",
    "victorian village",
    "arena district",
    "confluence",
    "olentangy",
    "university district",
    "south end",
    "driving park",
)

_FLOOD_NOTE_KEYWORDS_HIGH = re.compile(
    r"\b(flood\s*zone|100[- ]year|special flood|sfha|zone\s*a[e]?|floodplain|in flood)\b",
    re.I,
)
_FLOOD_NOTE_KEYWORDS_MOD = re.compile(
    r"\b(flood|drainage|storm\s*water|sewer\s*backup|water\s*table)\b",
    re.I,
)

_LATLON_HIGH_BOXES: tuple[tuple[str, float, float, float, float], ...] = (
    ("Scioto — Franklinton", 39.944, 39.972, -83.038, -83.002),
    ("Scioto — near Downtown west", 39.952, 39.968, -83.012, -82.995),
)
_LATLON_MOD_BOXES: tuple[tuple[str, float, float, float, float], ...] = (
    ("Olentangy — near confluence", 39.958, 39.982, -83.018, -82.998),
    ("Scioto — south / SW corridor", 39.928, 39.948, -83.030, -82.990),
)


@dataclass(frozen=True)
class FloodAssessment:
    score_10: float  # 10 = very low exposure
    label: str  # Low | Moderate | High
    note: str
    zone: str = ""
    zone_subty: str = ""


def _norm(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _label_rank(label: str) -> int:
    return {"High": 3, "Moderate": 2, "Low": 1}.get(label, 0)


def worse_label(a: str, b: str) -> str:
    return a if _label_rank(a) >= _label_rank(b) else b


def _worst(*items: FloodAssessment | None) -> FloodAssessment | None:
    found = [x for x in items if x is not None]
    if not found:
        return None
    return min(found, key=lambda x: x.score_10)


def _load_fema_cache() -> dict[str, dict]:
    if not _CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_fema_cache(cache: dict[str, dict]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def _cache_key(lat: float, lon: float) -> str:
    return f"{round(lat, 5)},{round(lon, 5)}"


def query_fema_nfhl(lat: float, lon: float) -> dict | None:
    """Return FEMA NFHL attributes at a WGS84 point, or None if unavailable."""
    key = _cache_key(lat, lon)
    cache = _load_fema_cache()
    if key in cache:
        return cache[key] or None

    params = urllib.parse.urlencode(
        {
            "where": "1=1",
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF,STATIC_BFE",
            "returnGeometry": "false",
            "f": "json",
        }
    )
    ctx = ssl.create_default_context(cafile=certifi.where())
    attrs: dict | None = None
    try:
        with urllib.request.urlopen(
            f"{FEMA_NFHL_QUERY}?{params}", context=ctx, timeout=30
        ) as resp:
            payload = json.loads(resp.read())
        features = payload.get("features") or []
        if features:
            attrs = features[0].get("attributes") or {}
    except (OSError, json.JSONDecodeError, urllib.error.URLError, ValueError):
        attrs = None

    cache[key] = attrs or {}
    _save_fema_cache(cache)
    return attrs


def _from_fema(attrs: dict) -> FloodAssessment:
    zone = str(attrs.get("FLD_ZONE") or "").strip().upper()
    subty = str(attrs.get("ZONE_SUBTY") or "").strip()
    subty_u = subty.upper()
    sfha = str(attrs.get("SFHA_TF") or "").strip().upper() == "T"

    if zone in _HIGH_ZONES or sfha:
        note = f"FEMA {zone}" + (f" — {subty}" if subty else "")
        return FloodAssessment(2.5, "High", note, zone, subty)

    if "LEVEE" in subty_u:
        return FloodAssessment(
            5.5,
            "Moderate",
            f"FEMA {zone} — levee-reduced (still waterway-adjacent)",
            zone,
            subty,
        )

    if "0.2 PCT" in subty_u or "0.2%" in subty_u:
        return FloodAssessment(
            6.5,
            "Moderate",
            f"FEMA {zone} — 0.2% annual chance flood hazard",
            zone,
            subty,
        )

    if zone in ("X", "AREA NOT INCLUDED", "D"):
        return FloodAssessment(
            8.5,
            "Low",
            f"FEMA zone {zone}" + (f" ({subty})" if subty else ""),
            zone,
            subty,
        )

    return FloodAssessment(
        6.0,
        "Moderate",
        f"FEMA zone {zone or 'unknown'}" + (f" — {subty}" if subty else ""),
        zone,
        subty,
    )


def _from_patterns(hay: str) -> FloodAssessment | None:
    for pat in _HIGH_RISK_PATTERNS:
        if pat in hay:
            return FloodAssessment(
                3.0,
                "High",
                f"Scioto corridor — {pat.title()}",
            )
    for pat in _MODERATE_RISK_PATTERNS:
        if pat in hay:
            return FloodAssessment(
                6.0,
                "Moderate",
                f"River-adjacent / drainage — {pat.title()}",
            )
    return None


def _from_notes(notes: object) -> FloodAssessment | None:
    text = str(notes or "").strip()
    if not text:
        return None
    if _FLOOD_NOTE_KEYWORDS_HIGH.search(text):
        return FloodAssessment(3.5, "High", "Listing notes: flood zone / SFHA")
    if _FLOOD_NOTE_KEYWORDS_MOD.search(text):
        return FloodAssessment(6.0, "Moderate", "Listing notes: drainage / flood")
    return None


def _from_lat_lon_boxes(lat: float, lon: float) -> FloodAssessment | None:
    for name, lat_min, lat_max, lon_min, lon_max in _LATLON_HIGH_BOXES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return FloodAssessment(3.0, "High", f"Near {name}")
    for name, lat_min, lat_max, lon_min, lon_max in _LATLON_MOD_BOXES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return FloodAssessment(6.0, "Moderate", f"Near {name}")
    return None


def assess_flood_risk(
    *,
    neighbourhood_label: object = None,
    city: object = None,
    flood_zone_notes: object = None,
    lat: float | None = None,
    lon: float | None = None,
) -> FloodAssessment | None:
    city_s = _norm(city)
    if city_s and city_s not in ("columbus", "ohio", ""):
        return _from_notes(flood_zone_notes)

    fema_hit: FloodAssessment | None = None
    if lat is not None and lon is not None:
        attrs = query_fema_nfhl(lat, lon)
        if attrs:
            fema_hit = _from_fema(attrs)
        box_hit = _from_lat_lon_boxes(lat, lon)
        fema_hit = _worst(fema_hit, box_hit)

    hay = _norm(neighbourhood_label)
    return _worst(
        fema_hit,
        _from_patterns(hay) if hay else None,
        _from_notes(flood_zone_notes),
    )


def merge_flood_score_10(llm_score: object, grounded: FloodAssessment | None) -> float | None:
    if grounded is None:
        try:
            return float(llm_score) if llm_score is not None else None
        except (TypeError, ValueError):
            return None
    try:
        llm_f = float(llm_score) if llm_score is not None else 10.0
    except (TypeError, ValueError):
        llm_f = 10.0
    return min(llm_f, grounded.score_10)


def _coords_for_extracted(extracted: dict) -> tuple[float | None, float | None]:
    try:
        from geocode import coordinates_for

        pid = extracted.get("property_id")
        if pid:
            coords = coordinates_for([str(pid)])
            if pid in coords:
                return coords[pid]
    except Exception:  # noqa: BLE001
        pass
    try:
        from transit_lookup import format_property_address, geocode_address

        address = format_property_address(extracted).strip()
        if address:
            lat, lon = geocode_address(address)
            return lat, lon
    except Exception:  # noqa: BLE001
        pass
    return None, None


def apply_flood_grounding(
    extracted: dict,
    scored: dict,
    *,
    neighbourhood_name: str = "",
) -> None:
    state = str(extracted.get("state") or "").strip().upper()
    if state and state not in ("OH", "OHIO"):
        return
    label = neighbourhood_name or resolve_neighbourhood_name(
        neighbourhood_name=scored.get("neighbourhood_name"),
        neighbourhood_research=scored.get("neighbourhood_research"),
        city=extracted.get("city"),
        state=extracted.get("state"),
        zip_code=extracted.get("zip"),
        listing_url=extracted.get("link"),
    )
    lat, lon = _coords_for_extracted(extracted)
    grounded = assess_flood_risk(
        neighbourhood_label=label,
        city=extracted.get("city"),
        flood_zone_notes=extracted.get("flood_zone_notes"),
        lat=lat,
        lon=lon,
    )
    regional = scored.setdefault("regional_assessment", {})
    merged = merge_flood_score_10(regional.get("flood_risk"), grounded)
    if merged is not None:
        regional["flood_risk"] = merged
    if grounded:
        regional["flood_grounding_note"] = grounded.note
        regional["flood_grounding_label"] = grounded.label
        if grounded.zone:
            regional["fema_flood_zone"] = grounded.zone
            regional["fema_flood_subty"] = grounded.zone_subty
        if grounded.label == "High" and merged is not None and merged < 5:
            flags = scored.setdefault("red_flags", [])
            note = f"Flood exposure: {grounded.note}"
            if note not in flags:
                flags.append(note)


def resolve_flood_assessment(
    *,
    property_id: str | None = None,
    neighbourhood_label: object = None,
    sheet_flood_label: object = None,
    flood_zone_notes: object = None,
    city: object = None,
    lat: float | None = None,
    lon: float | None = None,
) -> FloodAssessment | None:
    if lat is None and lon is None and property_id:
        try:
            from geocode import coordinates_for

            coords = coordinates_for([property_id])
            if property_id in coords:
                lat, lon = coords[property_id]
        except Exception:  # noqa: BLE001
            pass
    grounded = assess_flood_risk(
        neighbourhood_label=neighbourhood_label,
        city=city,
        flood_zone_notes=flood_zone_notes,
        lat=lat,
        lon=lon,
    )
    stored = str(sheet_flood_label or "").strip()
    if stored and grounded:
        final_label = worse_label(stored, grounded.label)
        if final_label != grounded.label:
            score = {"High": 3.0, "Moderate": 6.0, "Low": 8.5}[final_label]
            return FloodAssessment(score, final_label, grounded.note, grounded.zone, grounded.zone_subty)
    if grounded:
        return grounded
    if stored:
        icons = {"Low": 8.5, "Moderate": 6.0, "High": 3.0}
        return FloodAssessment(icons.get(stored, 6.0), stored, "From sheet")
    return None


def flood_display_text(assessment: FloodAssessment | None) -> str:
    if assessment is None:
        return "—"
    icons = {"Low": "🟢", "Moderate": "🟡", "High": "🔴"}
    icon = icons.get(assessment.label, "")
    zone_bit = f" {assessment.zone}" if assessment.zone else ""
    head = f"{icon} {assessment.label}{zone_bit}".strip()
    if assessment.note and assessment.note not in head:
        short = assessment.note if len(assessment.note) < 56 else assessment.note[:53] + "…"
        return f"{head} · {short}"
    return head


def flood_display_for_property(
    property_id: str,
    sheet_flood_label: object,
    neighbourhood_label: object,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> str:
    assessment = resolve_flood_assessment(
        property_id=property_id,
        neighbourhood_label=neighbourhood_label,
        sheet_flood_label=sheet_flood_label,
        lat=lat,
        lon=lon,
    )
    return flood_display_text(assessment)
