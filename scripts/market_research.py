"""Neighbourhood, appreciation, and rental research run during Analyze."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

from google.genai import types

from utils import (
    analysis_backend,
    generate_analysis_json,
    generate_content_with_retry,
    get_gemini_client,
    get_model_name,
    load_env,
    load_prompt,
    load_schema,
    parse_json_response,
    validate_against_schema,
)

_DEFAULT_SEARCH_TIMEOUT_SEC = 90.0
_SEARCH_MAX_RETRIES = 2
_JSON_MAX_RETRIES = 2


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


def _use_web_search() -> bool:
    load_env()
    val = os.getenv("MARKET_RESEARCH_USE_SEARCH", "false").strip().lower()
    return val in ("1", "true", "yes")


def _search_timeout_sec() -> float:
    load_env()
    raw = os.getenv("MARKET_RESEARCH_SEARCH_TIMEOUT_SEC", "").strip()
    if not raw:
        return _DEFAULT_SEARCH_TIMEOUT_SEC
    try:
        return max(30.0, float(raw))
    except ValueError:
        return _DEFAULT_SEARCH_TIMEOUT_SEC


def _gemini_research_model() -> str:
    load_env()
    return os.getenv("MARKET_RESEARCH_MODEL", "").strip() or get_model_name()


def _report(progress: Callable[[str], None] | None, message: str) -> None:
    if progress:
        progress(message)


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
    model = _gemini_research_model()
    response = generate_content_with_retry(
        client,
        model=model,
        contents=contents,
        config=config,
        max_retries=_SEARCH_MAX_RETRIES,
    )
    data = parse_json_response(response.text or "")
    if not isinstance(data, dict):
        raise ValueError("Market research returned non-object JSON.")
    validate_against_schema(data, schema)
    return data


def _json_research(prompt: str, parts: list[str], schema: dict[str, Any]) -> dict[str, Any]:
    return generate_analysis_json(
        system_prompt=prompt,
        text_parts=parts,
        schema=schema,
        models=[_gemini_research_model()],
        content_max_retries=_JSON_MAX_RETRIES,
    )


def research_market(
    extracted: dict[str, Any],
    *,
    transit: dict[str, Any] | None = None,
    sheet_tab: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, str]:
    """Research neighbourhood, appreciation, and rental demand for this address."""
    schema = load_schema("market_research_schema.json")
    prompt = load_prompt("market_research_prompt.md")
    parts = _user_parts(extracted, transit, sheet_tab)
    data: dict[str, Any]
    backend = analysis_backend()
    if backend == "gemini" and _use_web_search():
        client = get_gemini_client()
        timeout = _search_timeout_sec()
        _report(
            progress,
            f"Searching web for neighbourhood and rental data (up to {int(timeout)}s)…",
        )
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_with_search, client, parts, schema)
                data = future.result(timeout=timeout)
        except FuturesTimeoutError:
            _report(progress, "Web search timed out — using Gemini research…")
            data = _json_research(prompt, parts, schema)
        except Exception:
            _report(progress, "Web search failed — using Gemini research…")
            data = _json_research(prompt, parts, schema)
    else:
        _report(progress, "Researching neighbourhood and rental market…")
        data = _json_research(prompt, parts, schema)

    out = _empty_research()
    for key in out:
        out[key] = str(data.get(key) or "").strip()
    return out
