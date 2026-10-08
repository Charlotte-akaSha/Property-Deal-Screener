"""Verify Composer API (local OpenAI-compatible server) is reachable."""

from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

import certifi

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from composer_llm import composer_settings
from utils import analysis_backend, load_env


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def main() -> int:
    load_env()
    try:
        backend = analysis_backend()
    except RuntimeError as exc:
        print(f"FAIL  {exc}")
        return 1

    if backend == "gemini":
        print("SKIP  ANALYSIS_BACKEND=gemini (default) — analysis uses Gemini, not Composer.")
        print("      Set ANALYSIS_BACKEND=composer in .env only if you run a local Composer API bridge.")
        return 0

    base, key, model = composer_settings()
    print("OK  ANALYSIS_BACKEND=composer")
    print(f"    COMPOSER_API_BASE_URL={base}")
    print(f"    COMPOSER_MODEL={model}")

    url = f"{base.rstrip('/')}/models"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=5, context=_ssl_context()) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        print(f"OK  Composer API reachable ({url})")
        if body.strip().startswith("{"):
            data = json.loads(body)
            ids = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
            if ids:
                print(f"    models (sample): {', '.join(str(i) for i in ids[:5])}")
    except urllib.error.HTTPError as exc:
        print(f"WARN  Composer API HTTP {exc.code} at {url} (server is up; check API key)")
        return 0
    except urllib.error.URLError as exc:
        print(f"FAIL  Composer API not running: {exc.reason}")
        print()
        print("Nothing is listening on that URL. With ANALYSIS_BACKEND=composer, analysis needs")
        print("that server (or set COMPOSER_FALLBACK_TO_GEMINI=true to fall back). You need a")
        print("local OpenAI-compatible server, for example:")
        print("  • Install/run a Composer API proxy (macOS app) that exposes POST /v1/chat/completions")
        print("  • Paste your Cursor API key into that app, start the server (default port 8787)")
        print("  • Put these in .env (not only in the terminal):")
        print("      COMPOSER_API_BASE_URL=http://127.0.0.1:8787/v1")
        print("      COMPOSER_API_KEY=local")
        print("      COMPOSER_MODEL=composer-2.5-fast")
        print("      ANALYSIS_BACKEND=composer")
        print()
        print("Then: python3 scripts/check_composer.py")
        print("      python3 scripts/ingest_pending_listings.py")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
