"""Core pipeline: extract → slug → folder → score → local files → Sheets."""

from __future__ import annotations

import argparse
import json
import sys
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
    discover_images,
    generate_json_with_retry,
    get_gemini_client,
    image_parts_from_paths,
    image_parts_from_uploads,
    load_prompt,
    load_schema,
    load_strategy_raw,
    property_id_from_extracted,
    strategy_rules_without_weights,
)
from write_to_sheets import upsert_analysis


def extract_facts(
    listing_text: str,
    *,
    link: str = "",
    image_paths: list[Path] | None = None,
    image_uploads: list[tuple[str, bytes]] | None = None,
) -> dict[str, Any]:
    client = get_gemini_client()
    schema = load_schema("extraction_schema.json")
    prompt = load_prompt("extraction_prompt.md")
    user_parts: list[Any] = [
        "Listing URL (may be empty):\n" + (link or "(none)"),
        "Listing text:\n" + listing_text,
    ]
    if image_uploads:
        user_parts.extend(image_parts_from_uploads(image_uploads))
    elif image_paths:
        user_parts.extend(image_parts_from_paths(image_paths))
    extracted = generate_json_with_retry(
        client, system_prompt=prompt, user_parts=user_parts, schema=schema
    )
    if link and not extracted.get("link"):
        extracted["link"] = link
    if not extracted.get("status"):
        extracted["status"] = "New"
    return extracted


def score_property(extracted: dict[str, Any]) -> dict[str, Any]:
    client = get_gemini_client()
    schema = load_schema("scoring_schema.json")
    prompt = load_prompt("scoring_prompt.md")
    strategy = strategy_rules_without_weights(load_strategy_raw())
    weights = parse_weights()
    user_parts = [
        "Investment strategy rules:\n" + strategy,
        "Extracted property facts (JSON):\n" + json.dumps(extracted, indent=2),
    ]
    scored_raw = generate_json_with_retry(
        client, system_prompt=prompt, user_parts=user_parts, schema=schema
    )
    overall = compute_overall(scored_raw["categories"], weights)
    return {
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


def save_listing_inputs(
    folder: Path,
    *,
    listing_text: str,
    link: str = "",
    image_uploads: list[tuple[str, bytes]] | None = None,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    body = (link.strip() + "\n\n" if link.strip() else "") + listing_text.strip() + "\n"
    (folder / "listing.txt").write_text(body, encoding="utf-8")
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
    property_label: str | None = None,
    image_uploads: list[tuple[str, bytes]] | None = None,
    sheet_tab: str | None = None,
    skip_sheets: bool = False,
) -> dict[str, Any]:
    """Portal path: extract first, then create folder, score, persist, Sheets."""
    if not listing_text.strip():
        raise ValueError("Listing text is required.")
    if image_uploads and len(image_uploads) > MAX_PHOTOS:
        raise ValueError(f"At most {MAX_PHOTOS} photos allowed.")

    extracted = extract_facts(
        listing_text, link=link, image_uploads=image_uploads or []
    )
    property_id = property_id_from_extracted(extracted, property_label)
    folder = ROOT / "properties" / property_id
    save_listing_inputs(
        folder, listing_text=listing_text, link=link, image_uploads=image_uploads
    )
    scored = score_property(extracted)
    analysis = persist_local(
        folder,
        extracted=extracted,
        scored=scored,
        property_id=property_id,
        sheet_tab=sheet_tab,
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
    folder: Path, *, sheet_tab: str | None = None, skip_sheets: bool = False
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
    images = discover_images(folder)
    extracted = extract_facts(text, link=link, image_paths=images)
    property_id = folder.name
    scored = score_property(extracted)
    analysis = persist_local(
        folder,
        extracted=extracted,
        scored=scored,
        property_id=property_id,
        sheet_tab=sheet_tab,
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
