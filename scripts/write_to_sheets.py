"""Upsert analysis into Google Sheets, keyed on Property ID. Preserve Personal columns."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from utils import ROOT, join_list, load_env

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Property ID",
    "Link",
    "City",
    "State",
    "Overall",
    "Price",
    "Price/sqft",
    "Taxes",
    "HOA",
    "Estimated Insurance",
    "Estimated Rent",
    "Gross Annual Income",
    "House Size",
    "Land Size",
    "Bedrooms",
    "Bathrooms",
    "Walk to Station",
    "Train to City Center",
    "Total to City Center",
    "Year Built",
    "Garage",
    "Basement",
    "Heating",
    "Cooling",
    "Water",
    "Sewer",
    "Internet",
    "Recommendation",
    "Strengths",
    "Weaknesses",
    "Questions to Ask",
    "Red Flags",
    "Financial",
    "Location",
    "Property",
    "Appreciation",
    "Rental",
    "Management",
    "Lifestyle",
    "Climate",
    "Risk",
    "Wow Factor",
    "Notes",
    "Visit Date",
    "Final Decision",
    "Legal Units",
    "Trailer Fit",
    "Flood Risk",
    "Current Transit",
    "Future Transit",
    "Transit Plan Detail",
    "Appreciation Potential",
    "Rental Potential",
]

PERSONAL_COLUMN_LIST = ["Wow Factor", "Notes", "Visit Date", "Final Decision"]
PERSONAL_HEADERS = set(PERSONAL_COLUMN_LIST)
COMPARE_COLUMN_LIST = [
    "Legal Units",
    "Trailer Fit",
    "Flood Risk",
    "Current Transit",
    "Future Transit",
    "Transit Plan Detail",
    "Appreciation Potential",
    "Rental Potential",
]
UPDATABLE_COUNT = HEADERS.index("Wow Factor")


def _service_account_path() -> Path:
    load_env()
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path


def list_regions() -> list[str]:
    """Regional tabs from .env plus any regions/<Name>.md strategy files."""
    load_env()
    names: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        n = name.strip()
        if n and n not in seen:
            seen.add(n)
            names.append(n)

    raw = os.getenv("GOOGLE_SHEETS_REGIONS", "").strip()
    if raw:
        for part in raw.split(","):
            add(part)
    else:
        default = os.getenv("GOOGLE_SHEETS_TAB", "Properties").strip() or "Properties"
        add(default)

    regions_dir = ROOT / "regions"
    if regions_dir.is_dir():
        for path in sorted(regions_dir.glob("*.md")):
            if path.name.startswith("columbus_"):
                continue
            add(path.stem)

    columbus_strategy = regions_dir / "Columbus.md"
    if columbus_strategy.is_file():
        add("Columbus")

    return names


def open_worksheet(sheet_tab: str | None = None):
    load_env()
    sheet_id = os.getenv("GOOGLE_SHEETS_ID", "").strip()
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEETS_ID is missing in .env")
    creds_path = _service_account_path()
    if not creds_path.exists():
        raise RuntimeError(f"Service account file not found: {creds_path}")
    creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)
    tab = (sheet_tab or os.getenv("GOOGLE_SHEETS_TAB", "Properties")).strip() or "Properties"
    try:
        return spreadsheet.worksheet(tab)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=tab, rows=1000, cols=len(HEADERS))


def ensure_headers(ws) -> None:
    values = ws.row_values(1)
    if not values or not any(values):
        ws.update(range_name="A1", values=[HEADERS])
        return
    if len(values) < len(HEADERS) or values[: len(HEADERS)] != HEADERS:
        ws.update(range_name="A1", values=[HEADERS])


def sheet_url() -> str:
    load_env()
    sheet_id = os.getenv("GOOGLE_SHEETS_ID", "").strip()
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"


def analysis_to_row(analysis: dict[str, Any]) -> list[Any]:
    e = analysis["extracted"]
    s = analysis["scored"]
    c = s["categories"]
    t = analysis.get("transit") or {}
    walk = t.get("walk_to_station") or ""
    if t.get("nearest_station") and walk:
        walk = f"{walk} — {t['nearest_station']}"
    train = t.get("train_to_city_center") or ""
    if t.get("train_departure_at") and train:
        train = f"{train} (dep. {t['train_departure_at']})"
    if t.get("city_center") and train:
        train = f"{train} → {t['city_center']}"
    total = t.get("total_to_city_center") or ""
    if total and t.get("train_departure_at"):
        total = f"{total} (walk + train, dep. {t['train_departure_at']})"

    by_header: dict[str, Any] = {
        "Property ID": analysis["meta"]["property_id"],
        "Link": e.get("link", ""),
        "City": e.get("city", ""),
        "State": e.get("state", ""),
        "Overall": s.get("overall"),
        "Price": e.get("price"),
        "Price/sqft": e.get("price_per_sqft"),
        "Taxes": e.get("taxes"),
        "HOA": e.get("hoa"),
        "Estimated Insurance": e.get("estimated_insurance"),
        "Estimated Rent": e.get("estimated_rent"),
        "Gross Annual Income": e.get("gross_annual_income"),
        "House Size": e.get("house_sqft"),
        "Land Size": e.get("lot_sqft"),
        "Bedrooms": e.get("bedrooms"),
        "Bathrooms": e.get("bathrooms"),
        "Walk to Station": walk,
        "Train to City Center": train,
        "Total to City Center": total,
        "Year Built": e.get("year_built"),
        "Garage": e.get("garage", ""),
        "Basement": e.get("basement", ""),
        "Heating": e.get("heating", ""),
        "Cooling": e.get("cooling", ""),
        "Water": e.get("water", ""),
        "Sewer": e.get("sewer", ""),
        "Internet": e.get("internet", ""),
        "Recommendation": s.get("recommendation", ""),
        "Strengths": join_list(s.get("strengths")),
        "Weaknesses": join_list(s.get("weaknesses")),
        "Questions to Ask": join_list(s.get("questions_to_ask")),
        "Red Flags": join_list(s.get("red_flags")),
        "Financial": c.get("financial"),
        "Location": c.get("location"),
        "Property": c.get("property"),
        "Appreciation": c.get("appreciation"),
        "Rental": c.get("rental"),
        "Management": c.get("management"),
        "Lifestyle": c.get("lifestyle"),
        "Climate": c.get("climate"),
        "Risk": c.get("risk"),
        "Wow Factor": "",
        "Notes": "",
        "Visit Date": "",
        "Final Decision": "",
        **_compare_fields(e, s, t),
    }
    return [by_header[h] for h in HEADERS]


def _band_high_medium_low(score: object) -> str:
    try:
        value = float(score)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if value >= 7.5:
        return "High"
    if value >= 5:
        return "Medium"
    return "Low"


def _flood_label(score: object) -> str:
    """10 = very low flood exposure."""
    try:
        value = float(score)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if value >= 7.5:
        return "Low"
    if value >= 5:
        return "Moderate"
    return "High"


def _trailer_fit(score: object, garage: str) -> str:
    try:
        value = float(score)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        value = None
    if value is not None:
        if value >= 8:
            return "Yes"
        if value >= 6:
            return "Maybe"
        if value >= 3:
            return "Buildable"
        return "No"
    text = (garage or "").lower()
    if not text or text in {"none", "no", "n/a", "—"}:
        return "No"
    if any(word in text for word in ("rv", "carport", "oversized", "detached", "2-car", "3-car", "two-car", "three-car")):
        return "Maybe"
    if "garage" in text:
        return "Maybe"
    return ""


def _future_transit_label(catalyst: str, note: str) -> str:
    blob = f"{catalyst} {note}".lower()
    if "under construction" in blob:
        return "Under construction"
    mapping = {
        "none identified": "None",
        "speculative": "Possible",
        "possible": "Possible",
        "positive": "Planned",
        "major catalyst": "Funded",
    }
    return mapping.get((catalyst or "").strip().lower(), "")


def _current_transit_label(transit: dict[str, Any], location_score: object) -> str:
    quality = _band_high_medium_low(location_score)
    quality_word = {"High": "Strong", "Medium": "Fair", "Low": "Weak"}.get(quality, "")
    minutes = transit.get("walk_to_station_minutes")
    if quality_word and minutes:
        return f"{quality_word} · {int(minutes)} min walk"
    if quality_word:
        return quality_word
    return ""


def _compare_fields(
    extracted: dict[str, Any],
    scored: dict[str, Any],
    transit: dict[str, Any],
) -> dict[str, Any]:
    regional = scored.get("regional_assessment") or {}
    categories = scored.get("categories") or {}
    return {
        "Legal Units": extracted.get("legal_units"),
        "Trailer Fit": _trailer_fit(
            regional.get("trailer_storage_score"),
            str(extracted.get("garage") or ""),
        ),
        "Flood Risk": _flood_label(regional.get("flood_risk")),
        "Current Transit": _current_transit_label(transit, categories.get("location")),
        "Future Transit": _future_transit_label(
            str(regional.get("future_transit_catalyst") or ""),
            str(regional.get("future_transit_catalyst_note") or ""),
        ),
        "Transit Plan Detail": str(
            regional.get("future_transit_detail")
            or regional.get("future_transit_catalyst_note")
            or ""
        ).strip(),
        "Appreciation Potential": _band_high_medium_low(categories.get("appreciation")),
        "Rental Potential": _band_high_medium_low(categories.get("rental")),
    }


def find_row_by_property_id(ws, property_id: str) -> int | None:
    ids = ws.col_values(1)
    for idx, value in enumerate(ids[1:], start=2):
        if (value or "").strip() == property_id:
            return idx
    return None


def upsert_analysis(analysis: dict[str, Any], sheet_tab: str | None = None) -> dict[str, Any]:
    tab = sheet_tab or analysis.get("meta", {}).get("sheet_tab")
    ws = open_worksheet(tab)
    ensure_headers(ws)
    row = analysis_to_row(analysis)
    property_id = str(row[0])
    existing = find_row_by_property_id(ws, property_id)
    if existing is None:
        ws.append_row(row, value_input_option="USER_ENTERED")
        return {
            "action": "append",
            "property_id": property_id,
            "sheet_tab": ws.title,
            "sheet_url": sheet_url(),
        }
    # Update non-personal columns; leave Wow Factor / Notes / Visit Date / Final Decision untouched.
    prefix = row[:UPDATABLE_COUNT]
    end_col = gspread.utils.rowcol_to_a1(1, UPDATABLE_COUNT).replace("1", "")
    ws.update(
        range_name=f"A{existing}:{end_col}{existing}",
        values=[prefix],
        value_input_option="USER_ENTERED",
    )
    tail_start = HEADERS.index(COMPARE_COLUMN_LIST[0]) + 1
    tail = row[tail_start - 1 :]
    if tail:
        start_cell = gspread.utils.rowcol_to_a1(existing, tail_start)
        end_cell = gspread.utils.rowcol_to_a1(existing, len(HEADERS))
        ws.update(
            range_name=f"{start_cell}:{end_cell}",
            values=[tail],
            value_input_option="USER_ENTERED",
        )
    return {
        "action": "update",
        "property_id": property_id,
        "sheet_tab": ws.title,
        "sheet_url": sheet_url(),
        "row": existing,
    }


def upsert_from_folder(folder: Path, sheet_tab: str | None = None) -> dict[str, Any]:
    latest = folder / "latest.json"
    if not latest.exists():
        raise FileNotFoundError(f"No latest.json in {folder}")
    analysis = json.loads(latest.read_text(encoding="utf-8"))
    return upsert_analysis(analysis, sheet_tab=sheet_tab)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upsert property analysis to Google Sheets")
    parser.add_argument("property_dir", type=Path, help="Path to property folder with latest.json")
    parser.add_argument(
        "--region",
        help="Sheet tab name (defaults to sheet_tab stored in latest.json or .env)",
    )
    args = parser.parse_args(argv)
    folder = args.property_dir
    if not folder.is_absolute():
        folder = (Path.cwd() / folder).resolve()
    try:
        result = upsert_from_folder(folder, sheet_tab=args.region)
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"Sheets upsert failed: {exc}", file=sys.stderr)
        return 1
    print(f"Sheets {result['action']} OK for {result['property_id']} on tab '{result['sheet_tab']}'")
    print(result["sheet_url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
