"""Load property rows from Google Sheets, derive metrics, save personal edits."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from write_to_sheets import (
    HEADERS,
    PERSONAL_COLUMN_LIST,
    open_worksheet,
)

SCORE_COLUMNS = [
    "Financial",
    "Location",
    "Property",
    "Appreciation",
    "Rental",
    "Management",
    "Lifestyle",
    "Climate",
    "Risk",
]

NUMERIC_COLUMNS = [
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
    "Year Built",
    *SCORE_COLUMNS,
    "Wow Factor",
]

PERSONAL_COLUMN_LIST = ["Wow Factor", "Notes", "Visit Date", "Final Decision"]


def property_id_row_map(ws) -> dict[str, list[int]]:
    """Map Property ID -> 1-based sheet row numbers (column A, data rows only)."""
    ids = ws.col_values(1)
    result: dict[str, list[int]] = {}
    for row_num, value in enumerate(ids[1:], start=2):
        pid = (value or "").strip()
        if not pid:
            continue
        result.setdefault(pid, []).append(row_num)
    return result


def resolve_unique_sheet_row(ws, property_id: str, row_map: dict[str, list[int]] | None = None) -> int:
    """
    Resolve the live worksheet row for a Property ID.

    Raises ValueError when the ID is missing, duplicated, or the row fails verification.
    """
    pid = property_id.strip()
    if not pid:
        raise ValueError("Property ID is empty.")
    mapping = row_map if row_map is not None else property_id_row_map(ws)
    rows = mapping.get(pid, [])
    if not rows:
        raise ValueError(f"Property ID '{pid}' was not found on sheet '{ws.title}'.")
    if len(rows) > 1:
        raise ValueError(
            f"Property ID '{pid}' appears {len(rows)} times on sheet '{ws.title}' "
            f"(rows {rows}). Remove duplicates before saving."
        )
    sheet_row = rows[0]
    actual = (ws.cell(sheet_row, 1).value or "").strip()
    if actual != pid:
        raise ValueError(
            f"Row {sheet_row} on sheet '{ws.title}' expected Property ID '{pid}' "
            f"but found '{actual}'."
        )
    return sheet_row


def parse_commute_minutes(text: object) -> float | None:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    raw = str(text).strip()
    if not raw:
        return None
    hours = 0
    mins = 0
    h_match = re.search(r"(\d+)\s*hour", raw, re.I)
    m_match = re.search(r"(\d+)\s*min", raw, re.I)
    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        mins = int(m_match.group(1))
    if not h_match and not m_match:
        return None
    return float(hours * 60 + mins)


def to_number(series: pd.Series) -> pd.Series:
    """Coerce a sheet column to numbers, tolerating currency and percent formatting."""
    cleaned = (
        series.astype(str)
        .str.replace(r"[^\d.\-]", "", regex=True)
        .replace({"": None, "-": None, ".": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def load_region(region: str) -> pd.DataFrame:
    ws = open_worksheet(region)
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=[*HEADERS, "Region", "_sheet_row"])
    df = pd.DataFrame(records)
    for header in HEADERS:
        if header not in df.columns:
            df[header] = ""
    df["Region"] = region
    row_map = property_id_row_map(ws)
    df["_sheet_row"] = df["Property ID"].map(
        lambda pid: (
            row_map[str(pid).strip()][0]
            if str(pid).strip() in row_map and len(row_map[str(pid).strip()]) == 1
            else pd.NA
        )
    )
    return df


def load_properties(regions: list[str]) -> pd.DataFrame:
    frames = [load_region(r) for r in regions]
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[combined["Property ID"].astype(str).str.strip() != ""]
    return add_derived_columns(combined)


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in NUMERIC_COLUMNS:
        if col in out.columns:
            out[col] = to_number(out[col])

    out["Commute (min)"] = out.get("Total to City Center", pd.Series(dtype=object)).map(
        parse_commute_minutes
    )

    price = out["Price"]
    rent = out["Estimated Rent"]
    gross_annual = (
        out["Gross Annual Income"]
        if "Gross Annual Income" in out.columns
        else pd.Series(pd.NA, index=out.index)
    )
    rent = gross_annual.where(gross_annual.notna(), rent * 12) / 12
    taxes = out["Taxes"]
    insurance = out["Estimated Insurance"]
    hoa = out["HOA"] if "HOA" in out.columns else pd.Series(0, index=out.index)

    out["Gross yield %"] = (rent * 12 / price * 100).where(price > 0)
    annual_rent = rent * 12
    noi = annual_rent
    if "Taxes" in out.columns:
        noi = noi - out["Taxes"].fillna(0)
    if "Estimated Insurance" in out.columns:
        noi = noi - out["Estimated Insurance"].fillna(0)
    noi = noi - hoa.fillna(0) * 12
    out["Est. net yield %"] = (noi / price * 100).where((price > 0) & rent.notna())
    out["Gross rent label"] = [
        _gross_rent_label(monthly, annual=gross)
        for monthly, gross in zip(rent, gross_annual, strict=False)
    ]
    overall = out["Overall"] if "Overall" in out.columns else pd.Series(pd.NA, index=out.index)
    out["Match /100"] = overall * 10
    recommendations = (
        out["Recommendation"] if "Recommendation" in out.columns else pd.Series("", index=out.index)
    )
    out["Verdict"] = [
        _verdict_label(rec, score)
        for rec, score in zip(recommendations, overall, strict=False)
    ]
    out["Units"] = out.get("Legal Units", pd.Series(dtype=object)).map(_units_label)
    out["Trailer"] = [
        _prefer(stored, _trailer_from_garage(garage))
        for stored, garage in zip(
            out.get("Trailer Fit", pd.Series("", index=out.index)),
            out.get("Garage", pd.Series("", index=out.index)),
            strict=False,
        )
    ]
    out["Flood"] = out.get("Flood Risk", pd.Series("", index=out.index)).map(_flood_display)
    out["Transit now"] = [
        _prefer(stored, _transit_now_from_row(walk, location))
        for stored, walk, location in zip(
            out.get("Current Transit", pd.Series("", index=out.index)),
            out.get("Walk to Station", pd.Series("", index=out.index)),
            out.get("Location", pd.Series(dtype=float, index=out.index)),
            strict=False,
        )
    ]
    out["Transit future"] = out.get("Future Transit", pd.Series("", index=out.index)).map(
        lambda v: str(v).strip() or "—"
    )
    out["Appreciation label"] = [
        _prefer(stored, _band(score))
        for stored, score in zip(
            out.get("Appreciation Potential", pd.Series("", index=out.index)),
            out.get("Appreciation", pd.Series(dtype=float, index=out.index)),
            strict=False,
        )
    ]
    out["Rental potential"] = [
        _prefer(stored, _band(score))
        for stored, score in zip(
            out.get("Rental Potential", pd.Series("", index=out.index)),
            out.get("Rental", pd.Series(dtype=float, index=out.index)),
            strict=False,
        )
    ]
    out["Net monthly"] = rent - taxes / 12 - insurance / 12 - hoa.fillna(0)

    def score_profile(row: pd.Series) -> list[float]:
        vals: list[float] = []
        for col in SCORE_COLUMNS:
            v = row.get(col)
            if pd.notna(v):
                vals.append(float(v))
            else:
                vals.append(0.0)
        return vals

    out["Score profile"] = out.apply(score_profile, axis=1)
    return out


def _prefer(stored: object, fallback: str) -> str:
    text = "" if stored is None or (isinstance(stored, float) and pd.isna(stored)) else str(stored).strip()
    return text or fallback or "—"


def _band(score: object) -> str:
    try:
        value = float(score)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    if pd.isna(value):
        return "—"
    if value >= 7.5:
        return "High"
    if value >= 5:
        return "Medium"
    return "Low"


def _units_label(value: object) -> str:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    if pd.isna(number):
        return "—"
    if number == int(number):
        return str(int(number))
    return str(number)


def _gross_rent_label(monthly: object, *, annual: object = None) -> str:
    try:
        annual_f = float(annual)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        annual_f = None
    if annual_f is not None and not pd.isna(annual_f) and annual_f > 0:
        monthly_f = annual_f / 12
        return f"${monthly_f:,.0f}/mo · ${annual_f:,.0f}/yr (listing)"
    try:
        monthly_f = float(monthly)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    if pd.isna(monthly_f):
        return "—"
    return f"${monthly_f:,.0f}/mo · ${monthly_f * 12:,.0f}/yr"


def _verdict_label(recommendation: object, overall: object) -> str:
    rec = str(recommendation or "").strip()
    try:
        score = float(overall)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        score = 0.0
    if rec == "Worth visiting" and score >= 8:
        return "Buy"
    if rec == "Worth visiting":
        return "Strong candidate"
    if rec == "Save":
        return "Investigate"
    if rec == "Reject":
        return "Pass"
    return rec or "—"


def _trailer_from_garage(garage: object) -> str:
    text = str(garage or "").lower()
    if not text or text in {"none", "no", "n/a", "nan"}:
        return "No"
    if any(word in text for word in ("rv", "carport", "oversized", "detached", "2-car", "3-car", "two-car", "three-car")):
        return "Maybe"
    if "garage" in text:
        return "Maybe"
    return "—"


def _flood_display(value: object) -> str:
    label = str(value or "").strip()
    icons = {"Low": "🟢 Low", "Moderate": "🟡 Moderate", "High": "🔴 High"}
    return icons.get(label, label or "—")


def _transit_now_from_row(walk: object, location_score: object) -> str:
    quality = _band(location_score)
    word = {"High": "Strong", "Medium": "Fair", "Low": "Weak"}.get(quality, "")
    minutes = parse_commute_minutes(walk)
    if word and minutes is not None:
        return f"{word} · {int(minutes)} min walk"
    if word:
        return word
    text = str(walk or "").strip()
    return text or "—"


def personal_col_index(header: str) -> int:
    """1-based column index for a header name."""
    return HEADERS.index(header) + 1


def save_personal_edits(edits: pd.DataFrame) -> tuple[int, list[str]]:
    """Write personal columns only. Returns (rows updated, error messages)."""
    if edits.empty:
        return 0, []

    personal_start = HEADERS.index("Wow Factor") + 1
    personal_end = HEADERS.index("Final Decision") + 1
    start_cell = f"{_col_letter(personal_start)}"
    end_cell = f"{_col_letter(personal_end)}"

    count = 0
    errors: list[str] = []
    for region, group in edits.groupby("Region", sort=False):
        ws = open_worksheet(str(region))
        row_map = property_id_row_map(ws)
        batch: list[dict[str, Any]] = []
        for _, row in group.iterrows():
            property_id = str(row["Property ID"]).strip()
            try:
                sheet_row = resolve_unique_sheet_row(ws, property_id, row_map=row_map)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            values: list[Any] = []
            for col in PERSONAL_COLUMN_LIST:
                val = row.get(col, "")
                if pd.isna(val):
                    val = ""
                elif col == "Visit Date" and val != "":
                    val = str(val)[:10]
                values.append(val)
            batch.append(
                {
                    "range": f"{start_cell}{sheet_row}:{end_cell}{sheet_row}",
                    "values": [values],
                }
            )
        if batch:
            ws.batch_update(batch, value_input_option="USER_ENTERED")
            count += len(batch)
    return count, errors


def _col_letter(n: int) -> str:
    """1-based column index to A1 letter(s)."""
    result = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result
