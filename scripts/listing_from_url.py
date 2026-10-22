"""Best-effort import of listing text and photos from a public listing URL (Zillow)."""

from __future__ import annotations

import json
import os
import re
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import certifi

from utils import MAX_PHOTOS, load_env

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_ZILLOW_PHOTO_RE = re.compile(
    r"https://photos\.zillowstatic\.com/fp/[a-f0-9]+(?:-cc_ft_\d+)?\.jpg",
    re.IGNORECASE,
)


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _fetch_html_urllib(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _playwright_headed() -> bool:
    return os.environ.get("ZILLOW_PLAYWRIGHT_HEADED", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _playwright_profile_dir() -> Path | None:
    raw = os.environ.get("ZILLOW_BROWSER_PROFILE", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def _chrome_executable() -> str:
    override = os.environ.get("ZILLOW_CHROME_PATH", "").strip()
    if override:
        return override
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]
    for path in candidates:
        if Path(path).is_file():
            return path
    return "google-chrome"


def _cdp_endpoint() -> str:
    return os.environ.get("ZILLOW_CDP_URL", "http://127.0.0.1:9222").strip()


def _cdp_port() -> int:
    endpoint = _cdp_endpoint()
    m = re.search(r":(\d+)(?:/|$)", endpoint)
    return int(m.group(1)) if m else 9222


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


_chrome_proc: subprocess.Popen[bytes] | None = None
_visible_chrome_state: dict[str, Any] = {"playwright": None, "context": None}
_cdp_chrome_state: dict[str, Any] = {"playwright": None, "browser": None}


def _reset_visible_chrome_state() -> None:
    global _visible_chrome_state
    pw = _visible_chrome_state.get("playwright")
    ctx = _visible_chrome_state.get("context")
    if ctx is not None:
        try:
            ctx.close()
        except Exception:  # noqa: BLE001
            pass
    if pw is not None:
        try:
            pw.stop()
        except Exception:  # noqa: BLE001
            pass
    _visible_chrome_state = {"playwright": None, "context": None}


def _zillow_profile_dir() -> Path:
    return _playwright_profile_dir() or (
        Path(__file__).resolve().parent.parent / ".cache" / "zillow-chrome-profile"
    )


def _captcha_wait_sec() -> int:
    try:
        return max(30, int(os.environ.get("ZILLOW_CAPTCHA_WAIT_SEC", "300")))
    except ValueError:
        return 300


def _focus_chrome_window() -> None:
    if os.environ.get("ZILLOW_FOCUS_CHROME", "true").strip().lower() in ("0", "false", "no"):
        return
    chrome_app = "Google Chrome"
    if "Brave" in _chrome_executable():
        chrome_app = "Brave Browser"
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{chrome_app}" to activate'],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _listing_ready(html: str, url: str, dom_description: str) -> bool:
    if len(dom_description.strip()) >= 40:
        return True
    if _blocked_by_zillow(html):
        return False
    return _parsed_text_len(html, url) >= 80


def _wait_for_zillow_listing(page: Any, url: str) -> tuple[str, str]:
    """Keep the tab open until the listing loads or the user finishes Zillow verification."""
    max_sec = _captcha_wait_sec()
    deadline = time.time() + max_sec
    prompted = False
    while time.time() < deadline:
        try:
            html = page.content()
        except Exception:  # noqa: BLE001
            time.sleep(1)
            continue
        dom = _dom_description_from_page(page)
        if _listing_ready(html, url, dom):
            return html, dom
        if not prompted:
            _focus_chrome_window()
            print(
                "\n*** Zillow verification — use the Chrome window (same tab). "
                "Complete press-and-hold / captcha there. "
                f"Waiting up to {max_sec // 60} minutes; leave Chrome open. ***\n",
                flush=True,
            )
            prompted = True
        time.sleep(2)
    html = page.content()
    dom = _dom_description_from_page(page)
    return html, dom


def _fetch_via_cdp(url: str, timeout_ms: int = 90_000) -> tuple[str, str]:
    """Reuse one Chrome instance started with remote debugging (ZILLOW_AUTO_CDP)."""
    from playwright.sync_api import sync_playwright

    global _cdp_chrome_state
    endpoint = _ensure_chrome_cdp()
    if _cdp_chrome_state.get("browser") is None:
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(endpoint)
        _cdp_chrome_state = {"playwright": pw, "browser": browser}
    browser = _cdp_chrome_state["browser"]
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    return _wait_for_zillow_listing(page, url)


def _fetch_via_visible_chrome(url: str, timeout_ms: int = 90_000) -> tuple[str, str]:
    """Headed Chrome with a persistent profile — stays open for captcha (no CDP attach)."""
    from playwright.sync_api import sync_playwright

    global _visible_chrome_state
    if _visible_chrome_state.get("context") is None:
        profile = _zillow_profile_dir()
        profile.mkdir(parents=True, exist_ok=True)
        pw = None
        try:
            pw = sync_playwright().start()
            context = pw.chromium.launch_persistent_context(
                str(profile),
                channel="chrome",
                headless=False,
                viewport={"width": 1280, "height": 900},
                user_agent=_BROWSER_UA,
                args=["--disable-blink-features=AutomationControlled"],
            )
            _visible_chrome_state = {"playwright": pw, "context": context}
        except Exception as exc:
            if pw is not None:
                try:
                    pw.stop()
                except Exception:  # noqa: BLE001
                    pass
            _reset_visible_chrome_state()
            msg = str(exc).lower()
            if "already in use" in msg or "existing browser session" in msg:
                return _fetch_via_cdp(url, timeout_ms=timeout_ms)
            raise
    context = _visible_chrome_state["context"]
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    return _wait_for_zillow_listing(page, url)


def _ensure_chrome_cdp() -> str:
    """Start a dedicated Chrome with remote debugging when ZILLOW_AUTO_CDP is set."""
    global _chrome_proc
    endpoint = _cdp_endpoint()
    port = _cdp_port()
    if _port_open(port):
        return endpoint

    if os.environ.get("ZILLOW_AUTO_CDP", "").strip().lower() not in ("1", "true", "yes"):
        return endpoint

    profile = _playwright_profile_dir() or (
        Path(__file__).resolve().parent.parent / ".cache" / "zillow-chrome-profile"
    )
    profile.mkdir(parents=True, exist_ok=True)
    chrome = _chrome_executable()
    args = [
        chrome,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    ]
    _chrome_proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if _port_open(port):
            time.sleep(0.5)
            return endpoint
        time.sleep(0.25)
    raise RuntimeError(
        "Could not start Chrome for Zillow import. "
        f"Try manually: {chrome} --remote-debugging-port={port} "
        f'--user-data-dir="{profile}"'
    )


def _dom_description_from_page(page: Any) -> str:
    selectors = (
        '[data-testid="description"]',
        '[data-testid="home-description"]',
        'div[class*="Description"]',
        'div[class*="ds-description"]',
    )
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                text = loc.first.inner_text(timeout=5000).strip()
                if len(text) > 40:
                    return text
        except Exception:  # noqa: BLE001
            continue
    return ""


def _fetch_html_playwright_page(url: str, timeout_ms: int = 90_000) -> tuple[str, str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Install Playwright for Zillow URL import:\n"
            "  python3 -m pip install playwright\n"
            "  python3 -m playwright install chromium"
        ) from exc

    load_env()
    if _prefer_browser_fetch():
        if os.environ.get("ZILLOW_AUTO_CDP", "").strip().lower() in ("1", "true", "yes"):
            return _fetch_via_cdp(url, timeout_ms=timeout_ms)
        return _fetch_via_visible_chrome(url, timeout_ms=timeout_ms)

    headed = _playwright_headed()
    profile = _playwright_profile_dir()
    launch_kwargs: dict[str, Any] = {"channel": "chrome", "headless": not headed}

    with sync_playwright() as p:
        if profile is not None:
            profile.mkdir(parents=True, exist_ok=True)
            context = p.chromium.launch_persistent_context(
                str(profile),
                user_agent=_BROWSER_UA,
                viewport={"width": 1280, "height": 900},
                **launch_kwargs,
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            html, dom_description = _wait_for_zillow_listing(page, url)
            context.close()
            return html, dom_description
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(user_agent=_BROWSER_UA)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        html, dom_description = _wait_for_zillow_listing(page, url)
        browser.close()
        return html, dom_description


def _fetch_html_playwright(url: str, timeout_ms: int = 60_000) -> str:
    html, _ = _fetch_html_playwright_page(url, timeout_ms=timeout_ms)
    return html


def _listing_page_loaded(html: str) -> bool:
    lower = html.lower()
    if len(html) < 20_000:
        return False
    if "homedetails" not in lower and "zpid" not in lower:
        return False
    if re.search(r'"listPrice"\s*:\s*\d{4,}', html, re.IGNORECASE):
        return True
    if re.search(r'"price"\s*:\s*\d{4,}', html):
        return True
    if re.search(r"list\s*price\s*:\s*\$[\d,]+", html, re.IGNORECASE):
        return True
    return "__next_data__" in lower and len(html) > 100_000


def _blocked_by_zillow(html: str) -> bool:
    if _listing_page_loaded(html):
        return False
    lower = html.lower()
    return (
        "px-captcha" in lower
        or "access to this page has been denied" in lower
        or ("before you continue" in lower and "zillow" in lower)
    )


def fetch_html(url: str) -> str:
    html, _ = fetch_html_with_browser(url)
    return html


def _prefer_browser_fetch() -> bool:
    if os.environ.get("ZILLOW_AUTO_CDP", "").strip().lower() in ("1", "true", "yes"):
        return True
    if _playwright_profile_dir() is not None:
        return True
    return _playwright_headed()


def _parsed_text_len(html: str, url: str) -> int:
    return len(str(_parse_zillow_html(html, url).get("text") or ""))


def fetch_html_with_browser(url: str) -> tuple[str, str]:
    load_env()
    html: str | None = None
    dom_description = ""
    if not _prefer_browser_fetch():
        try:
            html = _fetch_html_urllib(url)
        except urllib.error.HTTPError as exc:
            if exc.code not in (403, 429):
                raise RuntimeError(f"Could not fetch listing page (HTTP {exc.code}).") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not fetch listing page: {exc.reason}") from exc

    needs_browser = (
        html is None
        or _blocked_by_zillow(html)
        or _parsed_text_len(html, url) < 80
    )
    if needs_browser:
        html, dom_description = _fetch_html_playwright_page(url)

    if not _listing_ready(html, url, dom_description):
        raise RuntimeError(
            "Zillow listing did not load (verification or captcha). "
            "Set ZILLOW_AUTO_CDP=true in .env, rerun the batch, and complete the check in Chrome. "
            "Increase ZILLOW_CAPTCHA_WAIT_SEC if you need more time (default 300)."
        )
    return html, dom_description


def _walk_find(obj: Any, keys: set[str]) -> Any:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and v not in (None, "", []):
                return v
            found = _walk_find(v, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _walk_find(item, keys)
            if found is not None:
                return found
    return None


def _parse_zillow_html(
    html: str,
    url: str,
    *,
    dom_description: str = "",
) -> dict[str, Any]:
    photo_urls: list[str] = []
    for match in _ZILLOW_PHOTO_RE.finditer(html):
        u = match.group(0)
        if u not in photo_urls:
            photo_urls.append(u)

    price: int | None = None
    days_on_zillow: int | None = None
    for pat in (
        r'"price"\s*:\s*(\d{4,9})',
        r'"listPrice"\s*:\s*(\d{4,9})',
        r'"unformattedPrice"\s*:\s*"?(\d{4,9})"?',
    ):
        m = re.search(pat, html)
        if m:
            price = int(m.group(1))
            break

    description = ""
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    if m:
        try:
            data = json.loads(m.group(1))
            desc = _walk_find(
                data,
                {
                    "description",
                    "homeDescription",
                    "listingDescription",
                    "marketingRemarks",
                },
            )
            if isinstance(desc, str):
                description = desc.strip()
            address = _walk_find(data, {"streetAddress", "address"}) or ""
            city = _walk_find(data, {"city"}) or ""
            state = _walk_find(data, {"state"}) or ""
            zip_code = _walk_find(data, {"zipcode", "zipCode", "zip"}) or ""
            if not price:
                raw_price = _walk_find(data, {"price", "listPrice", "unformattedPrice"})
                if isinstance(raw_price, (int, float)):
                    price = int(raw_price)
                elif isinstance(raw_price, str) and raw_price.isdigit():
                    price = int(raw_price)
            raw_dom = _walk_find(
                data,
                {
                    "timeOnZillow",
                    "daysOnZillow",
                    "daysOnSite",
                    "timeOnSite",
                    "daysOnMarket",
                },
            )
            if isinstance(raw_dom, (int, float)) and raw_dom >= 0:
                days_on_zillow = int(raw_dom)
            elif isinstance(raw_dom, str):
                dom_m = re.search(r"(\d+)", raw_dom)
                if dom_m:
                    days_on_zillow = int(dom_m.group(1))
        except json.JSONDecodeError:
            pass

    if days_on_zillow is None:
        dom_m = re.search(r"(\d+)\s+days?\s+on\s+Zillow", html, re.IGNORECASE)
        if dom_m:
            days_on_zillow = int(dom_m.group(1))

    if not description:
        m = re.search(r'"description"\s*:\s*"((?:\\.|[^"\\])*)"', html)
        if m:
            description = json.loads(f'"{m.group(1)}"')
    if dom_description and len(dom_description) > len(description):
        description = dom_description.strip()

    lines: list[str] = []
    if price:
        lines.append(f"List price: ${price:,}")
    if days_on_zillow is not None:
        lines.append(f"Days on Zillow: {days_on_zillow}")
    addr_m = re.search(
        r"(\d+\s+[\w\s]+),\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})",
        url,
    )
    if addr_m:
        lines.append(
            f"{addr_m.group(1).replace('-', ' ')}, {addr_m.group(2).strip()}, "
            f"{addr_m.group(3)} {addr_m.group(4)}"
        )
    mls = re.search(r"MLS\s*#?\s*(\d+)", html, re.IGNORECASE)
    if mls:
        lines.append(f"MLS #{mls.group(1)}")
    if description:
        lines.append("")
        lines.append(description)

    text = "\n".join(lines).strip() or description
    return {
        "text": text,
        "photo_urls": photo_urls[:MAX_PHOTOS],
        "link": url,
        "price": price,
        "days_on_zillow": days_on_zillow,
    }


def download_photo_bytes(urls: list[str]) -> list[tuple[str, bytes]]:
    ctx = _ssl_context()
    out: list[tuple[str, bytes]] = []
    for i, url in enumerate(urls[:MAX_PHOTOS], start=1):
        req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA})
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                data = resp.read()
        except Exception:
            continue
        out.append((f"photo{i}.jpg", data))
    return out


def import_from_url(url: str) -> dict[str, Any]:
    """Return text, link, photo_urls, and photo bytes for analyze_from_memory."""
    url = url.strip()
    if not url.startswith("http"):
        raise ValueError("Listing URL must start with http:// or https://")
    if "zillow.com" not in url.lower():
        raise ValueError("Only Zillow homedetails URLs are supported for auto-import today.")

    html, dom_description = fetch_html_with_browser(url)
    parsed = _parse_zillow_html(html, url, dom_description=dom_description)
    if len(str(parsed.get("text") or "")) < 80:
        raise RuntimeError(
            "Fetched the page but could not read listing text. Paste description manually "
            "or add screenshots."
        )
    photos = download_photo_bytes(parsed.get("photo_urls") or [])
    return {
        "text": parsed["text"],
        "link": url,
        "photo_urls": parsed.get("photo_urls") or [],
        "photos": photos,
        "price": parsed.get("price"),
    }


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Fetch Zillow listing text and photo URLs")
    parser.add_argument("url", help="Zillow homedetails URL")
    args = parser.parse_args()
    try:
        data = import_from_url(args.url)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(data["text"][:2000])
    print(f"\n--- photos: {len(data['photos'])} downloaded, urls: {len(data['photo_urls'])} ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
