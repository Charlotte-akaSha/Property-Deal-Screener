"""Rewrite Sheet rows from properties/*/latest.json (fixes column misalignment)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from utils import ROOT
from write_to_sheets import upsert_analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="Resync Google Sheets from local latest.json")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between API writes")
    parser.add_argument("--property-id", action="append", help="Only sync these Property IDs")
    args = parser.parse_args()

    paths = sorted((ROOT / "properties").glob("*/latest.json"))
    ok = skip = err = 0
    for path in paths:
        analysis = json.loads(path.read_text(encoding="utf-8"))
        pid = analysis.get("meta", {}).get("property_id") or path.parent.name
        if args.property_id and pid not in args.property_id:
            skip += 1
            continue
        tab = analysis.get("meta", {}).get("sheet_tab") or analysis.get("scored", {}).get("region")
        if not tab:
            skip += 1
            continue
        try:
            upsert_analysis(analysis, sheet_tab=tab)
            ok += 1
            print(f"OK  {pid} → {tab}", flush=True)
        except Exception as exc:  # noqa: BLE001
            err += 1
            print(f"FAIL {pid}: {exc}", flush=True)
        if args.delay > 0:
            time.sleep(args.delay)
    print(f"Done: {ok} ok, {skip} skipped, {err} failed", flush=True)
    return 0 if err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
