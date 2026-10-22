"""Load property rows from Google Sheets, derive metrics, save personal edits."""

from __future__ import annotations

import re
import time
from typing import Any

import pandas as pd

from flood_lookup import (
    flood_display_text,
    is_special_flood_hazard,
    resolve_flood_assessment,
)
from scoring import blend_with_personal_score, compute_overall, parse_weights, wow_factor_value
from neighbourhood import neighbourhood_display_label
from neighbourhood_tiers import (
    area_appreciation_note,
    area_rental_note,
    neighbourhood_search_tier,
    score_note_10,
)
from write_to_sheets import (
    HEADERS,
    PERSONAL_COLUMN_LIST,
    PERSONAL_SHEET_BLOCK,
    _listing_agent_cell,
    ensure_headers,
    open_worksheet,
)

JUDGMENT_VISIT = "Visit"
JUDGMENT_REJECT = "Reject"

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
    "Days on Zillow",
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
    last_exc: Exception | None = None
    records: list[dict[str, Any]] | None = None
    ws = None
    for attempt in range(3):
        try:
            ws = open_worksheet(region)
            records = ws.get_all_records()
            break
        except Exception as exc:  # noqa: BLE001 — retry transient Google API drops
            last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    if records is None or ws is None:
        assert last_exc is not None
        raise last_exc
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
    out["Units"] = out.get("Legal Units", pd.Series(dtype=object)).map(_units_label)
    out["Trailer"] = [
        _prefer(stored, _trailer_from_garage(garage))
        for stored, garage in zip(
            out.get("Trailer Fit", pd.Series("", index=out.index)),
            out.get("Garage", pd.Series("", index=out.index)),
            strict=False,
        )
    ]
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
    out["Neighbourhood display"] = [
        neighbourhood_display_label(
            n,
            c,
            s,
            neighbourhood_research=r,
            listing_url=link,
        )
        for n, c, s, r, link in zip(
            out.get("Neighbourhood", pd.Series("", index=out.index)),
            out.get("City", pd.Series("", index=out.index)),
            out.get("State", pd.Series("", index=out.index)),
            out.get("Neighbourhood Research", pd.Series("", index=out.index)),
            out.get("Link", pd.Series("", index=out.index)),
            strict=False,
        )
    ]
    out["Neighbourhood tier"] = out["Neighbourhood display"].map(neighbourhood_search_tier)
    appreciation_scores = out.get("Appreciation", pd.Series(dtype=float, index=out.index))
    rental_scores = out.get("Rental", pd.Series(dtype=float, index=out.index))
    out["Appreciation label"] = [
        _area_market_note(display, area_appreciation_note(display), score)
        for display, score in zip(out["Neighbourhood display"], appreciation_scores, strict=False)
    ]
    out["Rental potential"] = [
        _area_market_note(display, area_rental_note(display), score)
        for display, score in zip(out["Neighbourhood display"], rental_scores, strict=False)
    ]
    flood_stored = out.get("Flood Risk", pd.Series("", index=out.index))
    property_ids = out["Property ID"].astype(str)
    try:
        from geocode import coordinates_for

        coord_map = coordinates_for(property_ids.tolist())
    except Exception:  # noqa: BLE001
        coord_map = {}
    assessments = [
        resolve_flood_assessment(
            property_id=pid,
            neighbourhood_label=display,
            sheet_flood_label=stored,
            lat=coord_map.get(pid, (None, None))[0],
            lon=coord_map.get(pid, (None, None))[1],
        )
        for pid, stored, display in zip(
            property_ids, flood_stored, out["Neighbourhood display"], strict=False
        )
    ]
    out["Flood"] = [flood_display_text(item) for item in assessments]
    out["Flood gate"] = [is_special_flood_hazard(item) for item in assessments]
    _apply_flood_zone_scores(out, assessments)
    _apply_franklinton_climate(out)

    ai_overall = pd.to_numeric(
        out["Overall"] if "Overall" in out.columns else pd.Series(pd.NA, index=out.index),
        errors="coerce",
    ).astype(float)
    out["Overall AI"] = ai_overall
    wow = pd.to_numeric(
        out.get("Wow Factor", pd.Series(dtype=float, index=out.index)),
        errors="coerce",
    )
    blended = ai_overall.copy()
    for idx in out.index:
        if bool(out.at[idx, "Flood gate"]) or bool(out.at[idx, "Climate cap"]):
            continue
        personal = wow_factor_value(wow.at[idx])
        ai = ai_overall.at[idx]
        if personal is not None and pd.notna(ai):
            blended.at[idx] = blend_with_personal_score(float(ai), personal)
    out["Overall"] = blended
    overall = out["Overall"]
    out["Match /100"] = overall * 10
    recommendations = (
        out["Recommendation"] if "Recommendation" in out.columns else pd.Series("", index=out.index)
    )
    out["Verdict"] = [
        "Pass" if gate or climate else _verdict_label(rec, score)
        for gate, climate, rec, score in zip(
            out["Flood gate"], out["Climate cap"], recommendations, overall, strict=False
        )
    ]
    return out


def _apply_flood_zone_scores(out: pd.DataFrame, assessments: list) -> None:
    """Mapped FEMA flood zones: cap climate and risk, recompute match, force Reject."""
    if not any(is_special_flood_hazard(item) for item in assessments):
        return
    for col in ("Climate", "Risk", "Overall", *SCORE_COLUMNS):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype(float)
    try:
        weights = parse_weights()
    except ValueError:
        weights = None
    for idx, assessment in zip(out.index, assessments, strict=False):
        if not is_special_flood_hazard(assessment):
            continue
        cap = float(assessment.score_10)
        for col in ("Climate", "Risk"):
            if col not in out.columns:
                continue
            current = out.at[idx, col]
            try:
                value = float(current)
            except (TypeError, ValueError):
                value = cap
            if pd.isna(value):
                value = cap
            out.at[idx, col] = min(value, cap)
        if weights is not None:
            cats: dict[str, float] = {}
            complete = True
            for col in SCORE_COLUMNS:
                raw = out.at[idx, col] if col in out.columns else None
                try:
                    cats[col.lower()] = float(raw)
                except (TypeError, ValueError):
                    complete = False
                    break
            if complete:
                out.at[idx, "Overall"] = compute_overall(cats, weights)
        if "Recommendation" in out.columns:
            out.at[idx, "Recommendation"] = "Reject"


# Franklinton flood exposure. Climate's 11% weight cannot sink a high match on its own,
# so a failed climate score also caps the match.
_FRANKLINTON_CLIMATE = 1.0
_FRANKLINTON_OVERALL_CAP = 4.0


def _is_franklinton(label: object) -> bool:
    return "franklinton" in str(label or "").lower()


def _apply_franklinton_climate(out: pd.DataFrame) -> None:
    """Very low climate resilience in Franklinton, and a weak match score."""
    displays = out.get("Neighbourhood display", pd.Series("", index=out.index))
    flags = [_is_franklinton(label) for label in displays]
    out["Climate cap"] = flags
    if not any(flags):
        return
    for col in ("Climate", "Overall", *SCORE_COLUMNS):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype(float)
    try:
        weights = parse_weights()
    except ValueError:
        weights = None
    for idx, flag in zip(out.index, flags, strict=False):
        if not flag:
            continue
        if "Climate" in out.columns:
            out.at[idx, "Climate"] = _FRANKLINTON_CLIMATE
        recomputed = None
        if weights is not None:
            cats: dict[str, float] = {}
            complete = True
            for col in SCORE_COLUMNS:
                raw = out.at[idx, col] if col in out.columns else None
                try:
                    cats[col.lower()] = float(raw)
                except (TypeError, ValueError):
                    complete = False
                    break
            if complete:
                recomputed = compute_overall(cats, weights)
        if "Overall" in out.columns:
            if recomputed is None:
                try:
                    recomputed = float(out.at[idx, "Overall"])
                except (TypeError, ValueError):
                    recomputed = _FRANKLINTON_OVERALL_CAP
            out.at[idx, "Overall"] = min(recomputed, _FRANKLINTON_OVERALL_CAP)
        if "Recommendation" in out.columns:
            out.at[idx, "Recommendation"] = "Reject"


def _area_market_note(display: object, area_note: str | None, property_score: object) -> str:
    if area_note:
        return area_note
    if property_score is not None and not (isinstance(property_score, float) and pd.isna(property_score)):
        try:
            return score_note_10(float(property_score))
        except (TypeError, ValueError):
            pass
    return "—"


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


def personal_note_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("nan", "none") else text


def save_personal_rating(
    row: pd.Series,
    *,
    wow_factor: float | None,
    notes: str,
) -> tuple[int, list[str]]:
    """Update Wow Factor (your /10) and Notes for one property."""
    payload: dict[str, Any] = {
        "Property ID": row["Property ID"],
        "Region": row["Region"],
        "_sheet_row": row.get("_sheet_row"),
    }
    for col in PERSONAL_COLUMN_LIST:
        if col == "Wow Factor":
            payload[col] = "" if wow_factor is None else wow_factor
        elif col == "Notes":
            payload[col] = notes
        else:
            val = row.get(col, "")
            payload[col] = "" if pd.isna(val) else val
    return save_personal_edits(pd.DataFrame([payload]))


def judgment_reason_text(value: object) -> str:
    return personal_note_text(value)


def final_judgment_label(value: object) -> str:
    text = personal_note_text(value)
    if text in (JUDGMENT_VISIT, JUDGMENT_REJECT):
        return text
    return ""


def save_personal_judgment(
    row: pd.Series,
    *,
    decision: str | None,
    reason: str,
) -> tuple[int, list[str]]:
    """Final Decision = Visit | Reject; reason in appended Judgment reason column."""
    payload: dict[str, Any] = {
        "Property ID": row["Property ID"],
        "Region": row["Region"],
        "_sheet_row": row.get("_sheet_row"),
    }
    for col in PERSONAL_COLUMN_LIST:
        if col == "Final Decision":
            payload[col] = decision or ""
        elif col == "Judgment reason":
            payload[col] = reason
        elif col == "Wow Factor":
            val = row.get(col, "")
            payload[col] = "" if pd.isna(val) else val
        elif col == "Notes":
            payload[col] = personal_note_text(row.get("Notes"))
        else:
            val = row.get(col, "")
            payload[col] = "" if pd.isna(val) else val
    return save_personal_edits(pd.DataFrame([payload]))


def save_personal_note(row: pd.Series, notes: str) -> tuple[int, list[str]]:
    """Update only the Notes personal column for one property row."""
    return save_personal_rating(
        row,
        wow_factor=wow_factor_value(row.get("Wow Factor")),
        notes=notes,
    )


def property_id_for_link_substring(ws, needle: str) -> str | None:
    """Find Property ID whose Link column contains needle (e.g. Zillow zpid)."""
    if not needle:
        return None
    link_col = HEADERS.index("Link") + 1
    ids = ws.col_values(1)
    links = ws.col_values(link_col)
    for pid, link in zip(ids[1:], links[1:], strict=False):
        if needle in str(link or ""):
            return str(pid).strip() or None
    return None


def save_listing_agent_fields(
    property_id: str,
    region: str,
    *,
    name: str = "",
    company: str = "",
    phone: str = "",
) -> None:
    ws = open_worksheet(region)
    ensure_headers(ws)
    sheet_row = resolve_unique_sheet_row(ws, property_id)
    agent_col = HEADERS.index("Listing agent") + 1
    phone_col = HEADERS.index("Agent phone") + 1
    listing_agent = _listing_agent_cell(
        {
            "listing_agent_name": name,
            "listing_agent_company": company,
            "listing_agent_phone": phone,
        }
    )
    ws.batch_update(
        [
            {
                "range": f"{_col_letter(agent_col)}{sheet_row}",
                "values": [[listing_agent]],
            },
            {
                "range": f"{_col_letter(phone_col)}{sheet_row}",
                "values": [[phone.strip()]],
            },
        ],
        value_input_option="USER_ENTERED",
    )


def save_personal_edits(edits: pd.DataFrame) -> tuple[int, list[str]]:
    """Write personal columns only. Returns (rows updated, error messages)."""
    if edits.empty:
        return 0, []

    block_start = HEADERS.index("Wow Factor") + 1
    block_end = HEADERS.index("Final Decision") + 1
    block_start_cell = f"{_col_letter(block_start)}"
    block_end_cell = f"{_col_letter(block_end)}"
    reason_col = HEADERS.index("Judgment reason") + 1 if "Judgment reason" in HEADERS else None

    count = 0
    errors: list[str] = []
    for region, group in edits.groupby("Region", sort=False):
        ws = open_worksheet(str(region))
        ensure_headers(ws)
        row_map = property_id_row_map(ws)
        batch: list[dict[str, Any]] = []
        rows_ok = 0
        for _, row in group.iterrows():
            property_id = str(row["Property ID"]).strip()
            try:
                sheet_row = resolve_unique_sheet_row(ws, property_id, row_map=row_map)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            rows_ok += 1
            block_values: list[Any] = []
            for col in PERSONAL_SHEET_BLOCK:
                val = row.get(col, "")
                if pd.isna(val):
                    val = ""
                elif col == "Visit Date" and val != "":
                    val = str(val)[:10]
                block_values.append(val)
            batch.append(
                {
                    "range": f"{block_start_cell}{sheet_row}:{block_end_cell}{sheet_row}",
                    "values": [block_values],
                }
            )
            if reason_col is not None:
                reason_val = row.get("Judgment reason", "")
                if pd.isna(reason_val):
                    reason_val = ""
                batch.append(
                    {
                        "range": f"{_col_letter(reason_col)}{sheet_row}",
                        "values": [[reason_val]],
                    }
                )
        if batch:
            ws.batch_update(batch, value_input_option="USER_ENTERED")
            count += rows_ok
    return count, errors


def _col_letter(n: int) -> str:
    """1-based column index to A1 letter(s)."""
    result = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result
