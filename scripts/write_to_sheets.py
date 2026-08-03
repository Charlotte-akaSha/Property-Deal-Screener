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
    "Estimated Insurance",
    "Estimated Rent",
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
]

PERSONAL_HEADERS = {"Wow Factor", "Notes", "Visit Date", "Final Decision"}
UPDATABLE_COUNT = len(HEADERS) - len(PERSONAL_HEADERS)


def _service_account_path() -> Path:
    load_env()
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path


def list_regions() -> list[str]:
    """Regional tabs configured in .env (comma-separated)."""
    load_env()
    raw = os.getenv("GOOGLE_SHEETS_REGIONS", "").strip()
    if raw:
        return [name.strip() for name in raw.split(",") if name.strip()]
    default = os.getenv("GOOGLE_SHEETS_TAB", "Properties").strip() or "Properties"
    return [default]


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
        "Estimated Insurance": e.get("estimated_insurance"),
        "Estimated Rent": e.get("estimated_rent"),
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
    }
    return [by_header[h] for h in HEADERS]


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
    # Update only non-personal columns; leave Personal columns untouched
    updatable = row[:UPDATABLE_COUNT]
    end_col = gspread.utils.rowcol_to_a1(1, UPDATABLE_COUNT).replace("1", "")
    ws.update(
        range_name=f"A{existing}:{end_col}{existing}",
        values=[updatable],
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
