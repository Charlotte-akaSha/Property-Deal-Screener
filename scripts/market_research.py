"""Neighbourhood, appreciation, and rental research run during Analyze."""

from __future__ import annotations

import json
from typing import Any

from google.genai import types

from utils import (
    generate_content_with_retry,
    generate_json_with_retry,
    get_gemini_client,
    get_model_name,
    load_prompt,
    load_schema,
    model_candidates,
    parse_json_response,
    validate_against_schema,
)


def _location_line(extracted: dict[str, Any]) -> str:
    parts = [
        extracted.get("address") or "",
        extracted.get("city") or "",
        extracted.get("state") or "",
        extracted.get("zip") or "",
    ]
    return ", ".join(p.strip() for p in parts if p and str(p).strip()) or "(address unknown)"


def _user_parts(
    extracted: dict[str, Any],
    transit: dict[str, Any] | None,
    sheet_tab: str | None,
) -> list[str]:
    payload = {
        "address": extracted.get("address"),
        "city": extracted.get("city"),
        "state": extracted.get("state"),
        "zip": extracted.get("zip"),
        "link": extracted.get("link"),
        "price": extracted.get("price"),
        "legal_units": extracted.get("legal_units"),
        "bedrooms": extracted.get("bedrooms"),
        "bathrooms": extracted.get("bathrooms"),
        "estimated_rent": extracted.get("estimated_rent"),
        "gross_annual_income": extracted.get("gross_annual_income"),
        "rental_units_notes": extracted.get("rental_units_notes"),
        "flood_zone_notes": extracted.get("flood_zone_notes"),
        "sheet_tab": sheet_tab,
    }
    parts = [
        f"Property location: {_location_line(extracted)}",
        "Extracted facts (JSON):\n" + json.dumps(payload, indent=2),
        "Search this specific address and neighbourhood. "
        "Write neighbourhood, long-term appreciation, and rental-market research.",
    ]
    if transit:
        parts.append("Google Maps transit (authoritative):\n" + json.dumps(transit, indent=2))
    return parts


def _empty_research() -> dict[str, str]:
    return {
        "neighbourhood_name": "",
        "neighbourhood": "",
        "appreciation": "",
        "rental": "",
    }


def _with_search(client: Any, user_parts: list[str], schema: dict[str, Any]) -> dict[str, Any]:
    prompt = load_prompt("market_research_prompt.md")
    contents: list[Any] = [
        *user_parts,
        "Use Google Search. Return a single JSON object matching the schema — no markdown fences.",
        "Schema keys: neighbourhood_name, neighbourhood, appreciation, rental (all strings).",
    ]
    config = types.GenerateContentConfig(
        system_instruction=prompt,
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
    )
    last_error: Exception | None = None
    for model in model_candidates() or [get_model_name()]:
        try:
            response = generate_content_with_retry(
                client, model=model, contents=contents, config=config
            )
            data = parse_json_response(response.text or "")
            if not isinstance(data, dict):
                raise ValueError("Market research returned non-object JSON.")
            validate_against_schema(data, schema)
            return data
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    raise RuntimeError("Market research with search failed") from last_error


def research_market(
    extracted: dict[str, Any],
    *,
    transit: dict[str, Any] | None = None,
    sheet_tab: str | None = None,
) -> dict[str, str]:
    """Research neighbourhood, appreciation, and rental demand for this address."""
    schema = load_schema("market_research_schema.json")
    prompt = load_prompt("market_research_prompt.md")
    parts = _user_parts(extracted, transit, sheet_tab)
    client = get_gemini_client()
    try:
        data = _with_search(client, parts, schema)
    except Exception:
        data = generate_json_with_retry(
            client, system_prompt=prompt, user_parts=parts, schema=schema
        )
    out = _empty_research()
    for key in out:
        out[key] = str(data.get(key) or "").strip()
    return out
