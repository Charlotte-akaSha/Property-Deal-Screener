"""Core pipeline: extract → slug → folder → score → local files → Sheets."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from reports import persist_local
from scoring import compute_overall, parse_weights
from utils import (
    MAX_PHOTOS,
    ROOT,
    analysis_backend,
    analysis_fast_model,
    discover_images,
    fast_analysis_mode,
    generate_analysis_json,
    load_columbus_transit_reference,
    merge_json_schemas,
    load_prompt,
    load_schema,
    COLUMBUS_REGION,
    load_strategy_raw_for_region,
    property_id_from_extracted,
    resolve_sheet_tab,
    scoring_files_for_region,
    strategy_rules_without_weights,
)
from market_research import research_market
from transit_lookup import lookup_transit
from write_to_sheets import list_regions, upsert_analysis


def _region_for_transit(sheet_tab: str | None) -> str:
    if not sheet_tab:
        raise ValueError("Region is required for transit lookup.")
    return sheet_tab


def normalize_rent_fields(extracted: dict[str, Any]) -> dict[str, Any]:
    """Listing-stated gross annual income wins over inconsistent monthly estimates."""
    gross = extracted.get("gross_annual_income")
    monthly = extracted.get("estimated_rent")
    try:
        gross_f = float(gross) if gross is not None else None
    except (TypeError, ValueError):
        gross_f = None
    try:
        monthly_f = float(monthly) if monthly is not None else None
    except (TypeError, ValueError):
        monthly_f = None

    if gross_f is not None and gross_f > 0:
        implied_monthly = gross_f / 12
        if monthly_f is None or abs(monthly_f * 12 - gross_f) > 100:
            extracted["estimated_rent"] = round(implied_monthly, 2)
    elif monthly_f is not None and monthly_f > 0 and gross_f is None:
        extracted["gross_annual_income"] = round(monthly_f * 12, 2)
    return extracted


def extract_facts(
    listing_text: str,
    *,
    link: str = "",
    user_comments: str = "",
    image_paths: list[Path] | None = None,
    image_uploads: list[tuple[str, bytes]] | None = None,
) -> dict[str, Any]:
    schema = load_schema("extraction_schema.json")
    prompt = load_prompt("extraction_prompt.md")
    text_parts = [
        "Listing URL (may be empty):\n" + (link or "(none)"),
        "Listing text:\n" + listing_text,
    ]
    if user_comments.strip():
        text_parts.append("User comments (investor notes):\n" + user_comments.strip())
    extracted = generate_analysis_json(
        system_prompt=prompt,
        text_parts=text_parts,
        schema=schema,
        image_uploads=image_uploads,
        image_paths=image_paths,
    )
    if link and not extracted.get("link"):
        extracted["link"] = link
    if not extracted.get("status"):
        extracted["status"] = "New"
    return normalize_rent_fields(extracted)


def score_property(
    extracted: dict[str, Any],
    transit: dict[str, Any] | None = None,
    *,
    user_comments: str = "",
    sheet_tab: str | None = None,
    market_research: dict[str, str] | None = None,
    combine_market_research: bool = False,
) -> dict[str, Any]:
    prompt_name, schema_name = scoring_files_for_region(sheet_tab)
    schema = load_schema(schema_name)
    prompt = load_prompt(prompt_name)
    if combine_market_research:
        schema = merge_json_schemas(schema, load_schema("market_research_schema.json"))
        prompt = (
            prompt
            + "\n\n---\n\n"
            + load_prompt("market_research_prompt.md")
            + "\n\nInclude neighbourhood_name, neighbourhood, appreciation, and rental "
            "in the same JSON response as the scores."
        )
    strategy_md = load_strategy_raw_for_region(sheet_tab)
    strategy = strategy_rules_without_weights(strategy_md)
    weights = parse_weights(strategy_md)
    payload = dict(extracted)
    if transit:
        payload["transit"] = transit
    user_parts = [
        "Investment strategy rules:\n" + strategy,
        "Extracted property facts (JSON):\n" + json.dumps(payload, indent=2),
        "Note: transit walk/train times are computed via Google Maps, not from the listing.",
    ]
    if market_research:
        user_parts.append(
            "Address-specific market research (use for location, appreciation, and rental scores):\n"
            + json.dumps(market_research, indent=2)
        )
    if sheet_tab == COLUMBUS_REGION:
        user_parts.insert(
            1,
            "Columbus transit corridor reference:\n" + load_columbus_transit_reference(),
        )
    if user_comments.strip():
        user_parts.append(
            "User comments (investor notes — weigh alongside extracted facts when scoring):\n"
            + user_comments.strip()
        )
    fast_model = [analysis_fast_model()] if combine_market_research and analysis_fast_model() else None
    scored_raw = generate_analysis_json(
        system_prompt=prompt,
        text_parts=[str(p) for p in user_parts],
        schema=schema,
        models=fast_model,
        content_max_retries=2 if combine_market_research else None,
    )
    if combine_market_research:
        market_research = {
            "neighbourhood_name": str(scored_raw.get("neighbourhood_name") or ""),
            "neighbourhood": str(scored_raw.get("neighbourhood") or ""),
            "appreciation": str(scored_raw.get("appreciation") or ""),
            "rental": str(scored_raw.get("rental") or ""),
        }
    overall = compute_overall(scored_raw["categories"], weights)
    result: dict[str, Any] = {
        "categories": scored_raw["categories"],
        "overall": overall,
        "overall_computed_from_weights": True,
        "recommendation": scored_raw["recommendation"],
        "strengths": scored_raw.get("strengths") or [],
        "weaknesses": scored_raw.get("weaknesses") or [],
        "questions_to_ask": scored_raw.get("questions_to_ask") or [],
        "red_flags": scored_raw.get("red_flags") or [],
        "rationale": scored_raw.get("rationale") or "",
    }
    if scored_raw.get("regional_assessment"):
        result["regional_assessment"] = scored_raw["regional_assessment"]
    if market_research:
        result["neighbourhood_name"] = market_research.get("neighbourhood_name") or ""
        result["neighbourhood_research"] = market_research.get("neighbourhood") or ""
        result["appreciation_research"] = market_research.get("appreciation") or ""
        result["rental_research"] = market_research.get("rental") or ""
    if sheet_tab:
        result["region"] = sheet_tab
    return result


def _report_progress(progress: Callable[[str], None] | None, message: str) -> None:
    if progress:
        progress(message)


def save_listing_inputs(
    folder: Path,
    *,
    listing_text: str,
    link: str = "",
    user_comments: str = "",
    image_uploads: list[tuple[str, bytes]] | None = None,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    body = (link.strip() + "\n\n" if link.strip() else "") + listing_text.strip() + "\n"
    (folder / "listing.txt").write_text(body, encoding="utf-8")
    if user_comments.strip():
        (folder / "user_comments.txt").write_text(user_comments.strip() + "\n", encoding="utf-8")
    if not image_uploads:
        return
    for i, (name, data) in enumerate(image_uploads[:MAX_PHOTOS], start=1):
        suffix = Path(name).suffix.lower() or ".jpg"
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            suffix = ".jpg"
        (folder / f"photo{i}{suffix}").write_bytes(data)


def analyze_from_memory(
    listing_text: str,
    *,
    link: str = "",
    user_comments: str = "",
    property_label: str | None = None,
    image_uploads: list[tuple[str, bytes]] | None = None,
    sheet_tab: str | None = None,
    skip_sheets: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Portal path: extract first, then create folder, score, persist, Sheets."""
    if not listing_text.strip():
        raise ValueError("Listing text is required.")
    if image_uploads and len(image_uploads) > MAX_PHOTOS:
        raise ValueError(f"At most {MAX_PHOTOS} photos allowed.")

    comments = user_comments.strip()
    _report_progress(progress, "Extracting facts…")
    extracted = extract_facts(
        listing_text,
        link=link,
        user_comments=comments,
        image_uploads=image_uploads or [],
    )
    regions = list_regions()
    sheet_tab = resolve_sheet_tab(
        extracted,
        listing_text=listing_text,
        link=link,
        explicit=sheet_tab,
        regions=regions,
    )
    property_id = property_id_from_extracted(extracted, property_label)
    folder = ROOT / "properties" / property_id
    transit_region = _region_for_transit(sheet_tab)
    _report_progress(progress, "Looking up transit and saving listing…")
    with ThreadPoolExecutor(max_workers=2) as pool:
        transit_future = pool.submit(
            lookup_transit, extracted, sheet_tab=transit_region
        )
        save_future = pool.submit(
            save_listing_inputs,
            folder,
            listing_text=listing_text,
            link=link,
            user_comments=comments,
            image_uploads=image_uploads,
        )
        transit = transit_future.result()
        save_future.result()
    if fast_analysis_mode():
        _report_progress(
            progress,
            "Scoring + neighbourhood research (one step)…",
        )
        scored = score_property(
            extracted,
            transit=transit,
            user_comments=comments,
            sheet_tab=sheet_tab,
            combine_market_research=True,
        )
    else:
        _report_progress(progress, "Researching neighbourhood and rental market…")
        research = research_market(
            extracted,
            transit=transit,
            sheet_tab=sheet_tab,
            progress=progress,
        )
        _report_progress(progress, "Scoring against your strategy…")
        scored = score_property(
            extracted,
            transit=transit,
            user_comments=comments,
            sheet_tab=sheet_tab,
            market_research=research,
        )
    _report_progress(progress, "Saving results…")
    analysis = persist_local(
        folder,
        extracted=extracted,
        scored=scored,
        property_id=property_id,
        sheet_tab=sheet_tab,
        transit=transit,
    )

    sheets_result: dict[str, Any] | None = None
    sheets_error: str | None = None
    if not skip_sheets:
        try:
            sheets_result = upsert_analysis(analysis, sheet_tab=sheet_tab)
        except Exception as exc:  # noqa: BLE001
            sheets_error = str(exc)

    return {
        "analysis": analysis,
        "folder": str(folder),
        "sheets": sheets_result,
        "sheets_error": sheets_error,
    }


def analyze_from_folder(
    folder: Path,
    *,
    sheet_tab: str | None = None,
    skip_sheets: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """CLI path: folder already has listing.txt (+ optional photos)."""
    listing_path = folder / "listing.txt"
    if not listing_path.exists():
        raise FileNotFoundError(f"Missing listing.txt in {folder}")
    raw = listing_path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    link = ""
    text = raw
    if lines and lines[0].startswith("http"):
        link = lines[0].strip()
        text = "\n".join(lines[1:]).lstrip("\n")
    comments_path = folder / "user_comments.txt"
    user_comments = (
        comments_path.read_text(encoding="utf-8").strip() if comments_path.exists() else ""
    )
    images = discover_images(folder)
    _report_progress(progress, "Extracting facts…")
    extracted = extract_facts(
        text, link=link, user_comments=user_comments, image_paths=images
    )
    regions = list_regions()
    sheet_tab = resolve_sheet_tab(
        extracted,
        listing_text=text,
        link=link,
        explicit=sheet_tab,
        regions=regions,
    )
    property_id = folder.name
    _report_progress(progress, "Looking up transit…")
    transit = lookup_transit(extracted, sheet_tab=_region_for_transit(sheet_tab))
    if fast_analysis_mode():
        _report_progress(
            progress,
            "Scoring + neighbourhood research (one step)…",
        )
        scored = score_property(
            extracted,
            transit=transit,
            user_comments=user_comments,
            sheet_tab=sheet_tab,
            combine_market_research=True,
        )
    else:
        _report_progress(progress, "Researching neighbourhood and rental market…")
        research = research_market(
            extracted,
            transit=transit,
            sheet_tab=sheet_tab,
            progress=progress,
        )
        _report_progress(progress, "Scoring against your strategy…")
        scored = score_property(
            extracted,
            transit=transit,
            user_comments=user_comments,
            sheet_tab=sheet_tab,
            market_research=research,
        )
    _report_progress(progress, "Saving results…")
    analysis = persist_local(
        folder,
        extracted=extracted,
        scored=scored,
        property_id=property_id,
        sheet_tab=sheet_tab,
        transit=transit,
    )
    sheets_result = None
    sheets_error = None
    if not skip_sheets:
        try:
            sheets_result = upsert_analysis(analysis, sheet_tab=sheet_tab)
        except Exception as exc:  # noqa: BLE001
            sheets_error = str(exc)
    return {
        "analysis": analysis,
        "folder": str(folder),
        "sheets": sheets_result,
        "sheets_error": sheets_error,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze a property folder")
    parser.add_argument("property_dir", type=Path)
    parser.add_argument("--skip-sheets", action="store_true")
    parser.add_argument("--region", help="Google Sheet tab name (e.g. 'New York')")
    args = parser.parse_args(argv)
    folder = args.property_dir
    if not folder.is_absolute():
        folder = (Path.cwd() / folder).resolve()
    try:
        result = analyze_from_folder(
            folder, sheet_tab=args.region, skip_sheets=args.skip_sheets
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Analysis failed: {exc}", file=sys.stderr)
        return 1
    analysis = result["analysis"]
    scored = analysis["scored"]
    print(f"Property ID: {analysis['meta']['property_id']}")
    print(f"Overall: {scored['overall']}/10")
    print(f"Recommendation: {scored['recommendation']}")
    transit = analysis.get("transit") or {}
    if transit:
        print(
            f"Walk to station: {transit.get('walk_to_station')} ({transit.get('nearest_station')})"
        )
        print(
            f"Train to city center: {transit.get('train_to_city_center')} "
            f"(dep. {transit.get('train_departure_at')}) → {transit.get('city_center')}\n"
            f"Total to city center: {transit.get('total_to_city_center')} (walk + train)"
        )
    print(f"Saved to: {result['folder']}")
    if result["sheets_error"]:
        print(f"WARNING: analysis succeeded, Sheet update failed: {result['sheets_error']}")
        return 2
    if result["sheets"]:
        tab = result["sheets"].get("sheet_tab", "")
        print(f"Sheets: {result['sheets']['action']} on '{tab}' — {result['sheets']['sheet_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
