"""Local analysis.json / report.md writers."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import PROMPT_VERSION, get_model_name


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
        "## Strengths",
        *[f"- {x}" for x in s.get("strengths") or ["(none)"]],
        "",
        "## Weaknesses",
        *[f"- {x}" for x in s.get("weaknesses") or ["(none)"]],
        "",
        "## Red Flags",
        *[f"- {x}" for x in s.get("red_flags") or ["(none)"]],
        "",
        "## Questions to Ask",
        *[f"- {x}" for x in s.get("questions_to_ask") or ["(none)"]],
        "",
        "## Rationale",
        s.get("rationale") or "",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def persist_local(
    folder: Path,
    *,
    extracted: dict[str, Any],
    scored: dict[str, Any],
    property_id: str,
    sheet_tab: str | None = None,
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
    analysis_path = folder / f"analysis_{ts}.json"
    report_path = folder / f"report_{ts}.md"
    latest_path = folder / "latest.json"
    analysis_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    write_report_md(analysis, report_path)
    shutil.copyfile(analysis_path, latest_path)
    return analysis
