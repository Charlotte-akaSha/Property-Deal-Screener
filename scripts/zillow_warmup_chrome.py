"""Open the Zillow Chrome profile and wait while you pass verification once."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from utils import load_env

load_env()


def main() -> int:
    import os

    os.environ.setdefault("ZILLOW_AUTO_CDP", "true")
    from listing_from_url import _captcha_wait_sec, _fetch_via_visible_chrome

    wait = _captcha_wait_sec()
    print(
        "A Chrome window will open (Zillow profile).\n"
        "Complete any press-and-hold / captcha on the listing page.\n"
        f"The script waits up to {wait // 60} minutes.\n"
        "Run from project root: python3 scripts/zillow_warmup_chrome.py\n",
        flush=True,
    )
    url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://www.zillow.com/homedetails/98-100-N-Westmoor-Ave-Columbus-OH-43204/33872704_zpid/"
    )
    try:
        html, dom = _fetch_via_visible_chrome(url)
        print(f"OK — page length {len(html)}, description {len(dom)} chars.", flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Not ready yet: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
