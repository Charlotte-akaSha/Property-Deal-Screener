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
    "Address",
    "City",
    "State",
    "Link",
    "Status",
    "Price",
    "Price/sqft",
    "Taxes",
    "HOA",
    "Estimated Insurance",
    "Bedrooms",
    "Bathrooms",
    "House Size",
    "Land Size",
    "Year Built",
    "Garage",
    "Basement",
    "Heating",
    "Cooling",
    "Water",
    "Sewer",
    "Internet",
    "Overall",
    "Financial",
    "Location",
    "Property",
    "Appreciation",
    "Rental",
    "Management",
    "Lifestyle",
    "Climate",
    "Risk",
    "Recommendation",
    "Strengths",
    "Weaknesses",
    "Questions to Ask",
    "Red Flags",
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


def open_worksheet():
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
    tab = os.getenv("GOOGLE_SHEETS_TAB", "Properties").strip() or "Properties"
    try:
        return spreadsheet.worksheet(tab)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=tab, rows=1000, cols=len(HEADERS))


def ensure_headers(ws) -> None:
    values = ws.row_values(1)
    if not values or not any(values):
        ws.update(range_name="A1", values=[HEADERS])


def sheet_url() -> str:
    load_env()
    sheet_id = os.getenv("GOOGLE_SHEETS_ID", "").strip()
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"


def analysis_to_row(analysis: dict[str, Any]) -> list[Any]:
    e = analysis["extracted"]
    s = analysis["scored"]
    c = s["categories"]
    return [
        analysis["meta"]["property_id"],
        e.get("address", ""),
        e.get("city", ""),
        e.get("state", ""),
        e.get("link", ""),
        e.get("status", "New"),
        e.get("price"),
        e.get("price_per_sqft"),
        e.get("taxes"),
        e.get("hoa"),
        e.get("estimated_insurance"),
        e.get("bedrooms"),
        e.get("bathrooms"),
        e.get("house_sqft"),
        e.get("lot_sqft"),
        e.get("year_built"),
        e.get("garage", ""),
        e.get("basement", ""),
        e.get("heating", ""),
        e.get("cooling", ""),
        e.get("water", ""),
        e.get("sewer", ""),
        e.get("internet", ""),
        s.get("overall"),
        c.get("financial"),
        c.get("location"),
        c.get("property"),
        c.get("appreciation"),
        c.get("rental"),
        c.get("management"),
        c.get("lifestyle"),
        c.get("climate"),
        c.get("risk"),
        s.get("recommendation", ""),
        join_list(s.get("strengths")),
        join_list(s.get("weaknesses")),
        join_list(s.get("questions_to_ask")),
        join_list(s.get("red_flags")),
        "",  # Wow Factor
        "",  # Notes
        "",  # Visit Date
        "",  # Final Decision
    ]


def find_row_by_property_id(ws, property_id: str) -> int | None:
    ids = ws.col_values(1)
    for idx, value in enumerate(ids[1:], start=2):
        if (value or "").strip() == property_id:
            return idx
    return None


def upsert_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    ws = open_worksheet()
    ensure_headers(ws)
    row = analysis_to_row(analysis)
    property_id = str(row[0])
    existing = find_row_by_property_id(ws, property_id)
    if existing is None:
        ws.append_row(row, value_input_option="USER_ENTERED")
        return {"action": "append", "property_id": property_id, "sheet_url": sheet_url()}
    # Update only non-personal columns; leave Personal columns untouched
    updatable = row[:UPDATABLE_COUNT]
    end_col = gspread.utils.rowcol_to_a1(1, UPDATABLE_COUNT).replace("1", "")
    ws.update(
        range_name=f"A{existing}:{end_col}{existing}",
        values=[updatable],
        value_input_option="USER_ENTERED",
    )
    return {"action": "update", "property_id": property_id, "sheet_url": sheet_url(), "row": existing}


def upsert_from_folder(folder: Path) -> dict[str, Any]:
    latest = folder / "latest.json"
    if not latest.exists():
        raise FileNotFoundError(f"No latest.json in {folder}")
    analysis = json.loads(latest.read_text(encoding="utf-8"))
    return upsert_analysis(analysis)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upsert property analysis to Google Sheets")
    parser.add_argument("property_dir", type=Path, help="Path to property folder with latest.json")
    args = parser.parse_args(argv)
    folder = args.property_dir
    if not folder.is_absolute():
        folder = (Path.cwd() / folder).resolve()
    try:
        result = upsert_from_folder(folder)
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"Sheets upsert failed: {exc}", file=sys.stderr)
        return 1
    print(f"Sheets {result['action']} OK for {result['property_id']}")
    print(result["sheet_url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
