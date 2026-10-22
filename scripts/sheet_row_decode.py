"""Decode misaligned Google Sheet rows after agent columns were added to row 1 only."""

from __future__ import annotations

import re
from typing import Any

# Column layout before Listing agent / Agent phone (commit 022bf6a).
LEGACY_HEADERS_V59: tuple[str, ...] = (
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
    "Neighbourhood",
    "Neighbourhood Research",
    "Appreciation Research",
    "Rental Research",
    "Days on Zillow",
    "Judgment reason",
)

_CITY_LIKE = frozenset(
    {
        "columbus",
        "ossining",
        "montrose",
        "croton-on-hudson",
        "grove city",
        "worthington",
        "dublin",
        "bexley",
    }
)


def _cell(row: list[Any], index: int) -> str:
    if index >= len(row):
        return ""
    val = row[index]
    if val is None:
        return ""
    return str(val).strip()


def _is_price_like(text: str) -> bool:
    raw = text.replace(",", "").replace("$", "").strip()
    try:
        return float(raw) >= 10_000
    except ValueError:
        return False


def _has_agent_prefix(row: list[Any]) -> bool:
    """True when cols 3–5 hold agent data and legacy City/State/Overall were overwritten."""
    c2 = _cell(row, 2).lower()
    if not c2 or c2 in _CITY_LIKE:
        return False
    if "zillow.com" in c2 or c2.startswith("http"):
        return False
    return _is_price_like(_cell(row, 5))


def decode_physical_row(row: list[Any]) -> tuple[dict[str, str], str, str, str]:
    """
    Map a physical sheet row (unchanged cell positions) back to legacy field names.

    Returns (legacy_fields, agent_name, agent_company, agent_phone).
    """
    agent_name = agent_company = agent_phone = ""
    if _has_agent_prefix(row):
        agent_name = _cell(row, 2)
        agent_company = _cell(row, 3)
        agent_phone = _cell(row, 4)
        if agent_phone.upper().startswith("#ERROR"):
            agent_phone = ""

    legacy: dict[str, str] = {}
    for i, header in enumerate(LEGACY_HEADERS_V59):
        if _has_agent_prefix(row):
            if i < 2:
                legacy[header] = _cell(row, i)
            elif i < 5:
                legacy[header] = ""
            else:
                legacy[header] = _cell(row, i)
        else:
            legacy[header] = _cell(row, i)

    if _has_agent_prefix(row) and not legacy.get("City"):
        link = legacy.get("Link", "")
        if re.search(r"Columbus-OH", link, re.I):
            legacy["City"] = "Columbus"
            legacy["State"] = "OH"

    return legacy, agent_name, agent_company, agent_phone
