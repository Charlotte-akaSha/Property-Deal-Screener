"""Verify analysis API: Gemini skip, or OpenRouter / Composer reachability."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from composer_llm import probe_composer_api
from utils import analysis_backend, load_env


def main() -> int:
    load_env()
    try:
        backend = analysis_backend()
    except RuntimeError as exc:
        print(f"FAIL  {exc}")
        return 1

    if backend == "gemini":
        print("SKIP  ANALYSIS_BACKEND=gemini (default) — analysis uses Gemini, not Composer.")
        print("      Set ANALYSIS_BACKEND=composer or openrouter in .env for other backends.")
        return 0

    print(f"OK  ANALYSIS_BACKEND={backend}")
    ok, msg = probe_composer_api()
    if ok:
        print(f"OK  {msg}")
        return 0

    print(f"FAIL  {msg}")
    print()
    if backend == "openrouter":
        print("In .env add:")
        print("  OPENROUTER_API_KEY=sk-or-...   # https://openrouter.ai/keys")
        print("  OPENROUTER_MODEL=google/gemini-2.5-flash")
        print("See docs/openrouter-setup.md")
    else:
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
        print("See docs/composer-setup.md")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
