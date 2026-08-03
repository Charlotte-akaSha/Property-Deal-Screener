"""Verify .env, Gemini key presence, and Google Sheets service account auth."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from utils import ROOT, get_model_name, load_env


def main() -> int:
    load_env()
    ok = True
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        print(f"OK  GEMINI_API_KEY set (model default: {get_model_name()})")
    else:
        print("MISSING  GEMINI_API_KEY")
        ok = False

    maps_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if maps_key:
        print(f"OK  GOOGLE_MAPS_API_KEY set ({maps_key[:8]}...)")
    else:
        print("MISSING  GOOGLE_MAPS_API_KEY (required for Walk to Station / Train to City Center)")
        ok = False

    sheet_id = os.getenv("GOOGLE_SHEETS_ID", "").strip()
    if sheet_id:
        print(f"OK  GOOGLE_SHEETS_ID set ({sheet_id[:8]}...)")
    else:
        print("MISSING  GOOGLE_SHEETS_ID")
        ok = False

    creds = Path(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json"))
    if not creds.is_absolute():
        creds = ROOT / creds
    if creds.exists():
        print(f"OK  Service account file: {creds}")
        try:
            from write_to_sheets import open_worksheet, ensure_headers

            ws = open_worksheet()
            ensure_headers(ws)
            print(f"OK  Sheets access: worksheet '{ws.title}'")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL Sheets auth/open: {exc}")
            ok = False
    else:
        print(f"MISSING  Service account file: {creds}")
        ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
