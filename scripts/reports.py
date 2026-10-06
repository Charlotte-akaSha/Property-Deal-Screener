"""Local analysis.json / report.md writers."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import PROMPT_VERSION, get_model_name, join_list


def timestamp_slug() -> str:
    # Include microseconds so rapid re-analyzes never collide on the same second
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%f")


def write_report_md(analysis: dict[str, Any], path: Path) -> None:
    e = analysis["extracted"]
    s = analysis["scored"]
    title = e.get("address") or analysis["meta"]["property_id"]
    lines = [
        f"# {title}",
        "",
        f"**Overall Match:** {s['overall']}/10",
        "",
        f"**Recommendation:** {s['recommendation']}",
        "",
    ]
    t = analysis.get("transit") or {}
    if t:
        lines.extend(
            [
                "## Transit (Google Maps)",
                f"- **Walk to station:** {t.get('walk_to_station', '')} ({t.get('nearest_station', '')})",
                f"- **Train to city center:** {t.get('train_to_city_center', '')} "
                f"(dep. {t.get('train_departure_at', 'Mon 8:00 AM')}) → {t.get('city_center', '')}",
                f"- **Total to city center:** {t.get('total_to_city_center', '')} (walk + train)",
                "",
            ]
        )
    ra = s.get("regional_assessment")
    if ra:
        lines.extend(
            [
                "## Columbus accessibility",
                f"- **Current transit:** {ra.get('current_transit')}/10 (Tier {ra.get('transit_tier')})",
                f"- **Future transit investment:** {ra.get('future_transit_investment')}/10",
                f"- **Transit appreciation potential:** {ra.get('transit_appreciation_potential')}/10",
                f"- **Green / low-density:** {ra.get('green_low_density_quality')}/10",
                f"- **Flood risk (10=low):** {ra.get('flood_risk')}/10",
                f"- **Future catalyst:** {ra.get('future_transit_catalyst')}",
                f"- **Multi-unit / income:** {ra.get('multi_unit_score')}/10 "
                f"(Tier {ra.get('multi_unit_property_tier')})",
                f"- **Owner-occupancy fit:** {ra.get('owner_occupancy_fit')}/10",
                f"- **Trailer storage:** {ra.get('trailer_storage_score')}/10",
                f"- **Combined investment fit:** {ra.get('combined_investment_fit')}/10",
                "",
                ra.get("future_transit_catalyst_note") or "",
                "",
                ra.get("final_strategy_answer") or "",
                "",
            ]
        )
    lines.extend(
        [
            "## Strengths",
            join_list(s.get("strengths")) or "(none)",
            "",
            "## Weaknesses",
            join_list(s.get("weaknesses")) or "(none)",
            "",
            "## Red Flags",
            join_list(s.get("red_flags")) or "(none)",
            "",
            "## Questions to Ask",
            join_list(s.get("questions_to_ask")) or "(none)",
            "",
            "## Rationale",
            s.get("rationale") or "",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def persist_local(
    folder: Path,
    *,
    extracted: dict[str, Any],
    scored: dict[str, Any],
    property_id: str,
    sheet_tab: str | None = None,
    transit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    folder.mkdir(parents=True, exist_ok=True)
    ts = timestamp_slug()
    meta: dict[str, Any] = {
        "property_id": property_id,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "model": get_model_name(),
        "prompt_version": PROMPT_VERSION,
    }
    if sheet_tab:
        meta["sheet_tab"] = sheet_tab
    analysis = {
        "extracted": extracted,
        "scored": scored,
        "meta": meta,
    }
    if transit:
        analysis["transit"] = transit
    analysis_path = folder / f"analysis_{ts}.json"
    report_path = folder / f"report_{ts}.md"
    latest_path = folder / "latest.json"
    analysis_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    write_report_md(analysis, report_path)
    shutil.copyfile(analysis_path, latest_path)
    return analysis
