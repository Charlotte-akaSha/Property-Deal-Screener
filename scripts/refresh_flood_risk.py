"""Re-run FEMA + Columbus flood grounding without LLM re-analysis."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from flood_lookup import apply_flood_grounding, flood_display_text, resolve_flood_assessment
from utils import ROOT
from write_to_sheets import _flood_label, list_regions, patch_flood_risk_on_sheet


def _property_dirs(only: str | None) -> list[Path]:
    base = ROOT / "properties"
    if not base.is_dir():
        return []
    dirs = sorted(p for p in base.iterdir() if p.is_dir() and (p / "latest.json").is_file())
    if not only:
        return dirs
    needle = only.lower()
    return [d for d in dirs if needle in d.name.lower()]


def refresh_folder(folder: Path, *, write_sheet: bool, dry_run: bool) -> dict[str, str]:
    latest_path = folder / "latest.json"
    analysis = json.loads(latest_path.read_text(encoding="utf-8"))
    extracted = dict(analysis.get("extracted") or {})
    scored = dict(analysis.get("scored") or {})
    meta = analysis.get("meta") or {}
    property_id = str(meta.get("property_id") or folder.name)
    sheet_tab = meta.get("sheet_tab") or list_regions()[0]

    extracted["property_id"] = property_id
    apply_flood_grounding(
        extracted,
        scored,
        neighbourhood_name=str(scored.get("neighbourhood_name") or ""),
    )

    regional = scored.get("regional_assessment") or {}
    flood_score = regional.get("flood_risk")
    sheet_label = _flood_label(flood_score)

    from neighbourhood import neighbourhood_display_label

    display = neighbourhood_display_label(
        scored.get("neighbourhood_name"),
        extracted.get("city"),
        extracted.get("state"),
        neighbourhood_research=scored.get("neighbourhood_research"),
        listing_url=extracted.get("link"),
    )
    assessment = resolve_flood_assessment(
        property_id=property_id,
        neighbourhood_label=display,
        sheet_flood_label=sheet_label,
    )
    compare_text = flood_display_text(assessment)

    if not dry_run:
        analysis["extracted"] = extracted
        analysis["scored"] = scored
        latest_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        if write_sheet and sheet_label:
            patch_flood_risk_on_sheet(property_id, sheet_label, sheet_tab=sheet_tab)

    return {
        "property_id": property_id,
        "flood_risk": sheet_label or "—",
        "flood_score": str(flood_score) if flood_score is not None else "",
        "compare": compare_text,
        "fema_zone": str(regional.get("fema_flood_zone") or ""),
    }


def refresh_property_ids(
    property_ids: Iterable[str],
    *,
    write_sheet: bool = True,
) -> tuple[list[dict[str, str]], list[tuple[str, str]]]:
    """Refresh flood for Property IDs that have a local properties/<id>/latest.json."""
    wanted = {str(pid).strip() for pid in property_ids if str(pid).strip()}
    if not wanted:
        return [], []

    folders = {p.name: p for p in _property_dirs(None)}
    updated: list[dict[str, str]] = []
    errors: list[tuple[str, str]] = []
    missing: list[str] = []

    for pid in sorted(wanted):
        folder = folders.get(pid)
        if folder is None:
            missing.append(pid)
            continue
        try:
            updated.append(refresh_folder(folder, write_sheet=write_sheet, dry_run=False))
        except Exception as exc:  # noqa: BLE001
            errors.append((pid, str(exc)))

    for pid in missing:
        errors.append((pid, "No local analysis folder (re-analyze once to create properties/<id>)"))

    return updated, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh FEMA/heuristic flood risk for saved properties (no LLM)."
    )
    parser.add_argument(
        "--only",
        help="Substring filter on property folder name (e.g. Franklinton, Sullivant)",
    )
    parser.add_argument(
        "--skip-sheets",
        action="store_true",
        help="Update latest.json only; do not write Google Sheets",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without saving",
    )
    args = parser.parse_args(argv)

    folders = _property_dirs(args.only)
    if not folders:
        print("No property folders with latest.json matched.", file=sys.stderr)
        return 1

    for folder in folders:
        try:
            result = refresh_folder(
                folder,
                write_sheet=not args.skip_sheets,
                dry_run=args.dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {folder.name}: {exc}", file=sys.stderr)
            continue
        zone = f" FEMA {result['fema_zone']}" if result["fema_zone"] else ""
        print(
            f"{result['property_id']}: Sheet={result['flood_risk']}{zone} "
            f"(score {result['flood_score'] or '—'}) — {result['compare']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
