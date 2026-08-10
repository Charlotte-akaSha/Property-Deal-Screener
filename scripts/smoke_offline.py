"""Offline smoke tests (no Gemini / Sheets credentials required)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from reports import persist_local
from scoring import compute_overall, parse_weights
from utils import (
    ROOT,
    load_schema,
    property_id_from_extracted,
    strategy_rules_without_weights,
    validate_against_schema,
)
from write_to_sheets import HEADERS, PERSONAL_HEADERS, UPDATABLE_COUNT, analysis_to_row


def main() -> int:
    weights = parse_weights()
    assert abs(sum(weights.values()) - 1.0) < 0.001
    assert "risk" in weights

    rules = strategy_rules_without_weights()
    assert "weights:" not in rules
    assert "Buy and hold" in rules or "buy and hold" in rules.lower()

    extract_schema = load_schema("extraction_schema.json")
    score_schema = load_schema("scoring_schema.json")

    extracted = {
        "address": "100 Oak Street",
        "city": "Greenwood Lake",
        "state": "NY",
        "zip": "10925",
        "link": "https://example.com/listings/sample-100-oak-street",
        "status": "New",
        "price": 425000,
        "price_per_sqft": 293.1,
        "taxes": 8200,
        "hoa": 0,
        "estimated_insurance": 1800,
        "estimated_rent": 2800,
        "bedrooms": 3,
        "bathrooms": 2,
        "house_sqft": 1450,
        "lot_sqft": 12197,
        "year_built": 1988,
        "garage": "1-car attached",
        "basement": "Full unfinished",
        "heating": "Oil forced air",
        "cooling": "Central air",
        "water": "Well",
        "sewer": "Septic",
        "internet": "",
        "condition_notes": "Move-in ready",
        "flood_zone_notes": "No known flood zone issues disclosed",
    }
    validate_against_schema(extracted, extract_schema)

    categories = {k: 8.0 for k in weights}
    scored_model = {
        "categories": categories,
        "recommendation": "Worth visiting",
        "strengths": ["Commuter location"],
        "weaknesses": ["Oil heat"],
        "red_flags": [],
        "questions_to_ask": ["Septic inspection?"],
        "rationale": "Solid buy-and-hold candidate.",
    }
    validate_against_schema(scored_model, score_schema)
    overall = compute_overall(categories, weights)
    assert overall == 8.0

    pid = property_id_from_extracted(extracted)
    assert pid == "100_Oak_Street_Greenwood_Lake_NY"

    scored = {
        **{k: scored_model[k] for k in (
            "categories", "recommendation", "strengths", "weaknesses",
            "questions_to_ask", "red_flags", "rationale",
        )},
        "overall": overall,
        "overall_computed_from_weights": True,
    }
    transit = {
        "nearest_station": "Ossining Metro-North",
        "walk_to_station": "18 mins walk (0.9 mi)",
        "walk_to_station_minutes": 18,
        "train_to_city_center": "1 hour 5 mins",
        "train_to_city_center_minutes": 65,
        "total_to_city_center": "1 hour 23 mins",
        "total_to_city_center_minutes": 83,
        "train_departure_at": "Mon 8:00 AM EDT",
        "city_center": "Grand Central Terminal, New York, NY",
        "source": "google_maps",
    }

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / pid
        analysis = persist_local(
            folder,
            extracted=extracted,
            scored=scored,
            property_id=pid,
            transit=transit,
        )
        assert (folder / "latest.json").exists()
        reports = list(folder.glob("report_*.md"))
        analyses = list(folder.glob("analysis_*.json"))
        assert len(reports) == 1 and len(analyses) == 1
        # second run creates second timestamped pair
        persist_local(folder, extracted=extracted, scored=scored, property_id=pid)
        assert len(list(folder.glob("analysis_*.json"))) == 2

    assert UPDATABLE_COUNT == len(HEADERS) - len(PERSONAL_HEADERS)
    row = analysis_to_row(analysis)
    assert len(row) == len(HEADERS)
    assert row[0] == pid
    walk_col = HEADERS.index("Walk to Station")
    train_col = HEADERS.index("Train to City Center")
    assert "Ossining Metro-North" in row[walk_col]
    assert "Grand Central" in row[train_col]
    total_col = HEADERS.index("Total to City Center")
    assert "walk + train" in row[total_col]
    assert row[-4:] == ["", "", "", ""]  # Personal blank on write payload

    fixture = ROOT / "fixtures" / "sample_listing.txt"
    assert fixture.exists() and "100 Oak Street" in fixture.read_text(encoding="utf-8")

    from sheets_data import add_derived_columns, parse_commute_minutes  # noqa: E402

    assert parse_commute_minutes("1 hour 23 mins (walk + train)") == 83.0
    assert parse_commute_minutes("") is None

    sample = pd.DataFrame(
        [
            {
                "Property ID": "Test_Prop",
                # Sheets returns money columns as formatted strings
                "Price": "$400,000",
                "Estimated Rent": "$2,500",
                "Taxes": "$6,000",
                "Estimated Insurance": "$1,800",
                "Total to City Center": "45 mins (walk + train)",
                "Financial": 8,
                "Location": 7,
                "Property": 8,
                "Appreciation": 7,
                "Rental": 8,
                "Management": 7,
                "Lifestyle": 6,
                "Climate": 8,
                "Risk": 7,
            }
        ]
    )
    derived = add_derived_columns(sample)
    assert derived["Commute (min)"].iloc[0] == 45.0
    assert derived["Price"].iloc[0] == 400000
    assert abs(derived["Gross yield %"].iloc[0] - 7.5) < 0.01
    assert abs(derived["Net monthly"].iloc[0] - 1850.0) < 0.01
    assert len(derived["Score profile"].iloc[0]) == 9

    print("Offline smoke tests passed.")
    print("Next: copy .env.example → .env, add Gemini + Sheets credentials, then:")
    print("  python scripts/check_credentials.py")
    print("  python scripts/analyze_property.py <property_dir> --skip-sheets")
    print("  streamlit run streamlit_app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
