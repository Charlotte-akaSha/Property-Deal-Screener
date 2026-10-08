"""Best-effort import of listing text and photos from a public listing URL (Zillow)."""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
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


def _fetch_html_playwright(url: str, timeout_ms: int = 60_000) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Zillow blocked the simple download (HTTP 403). Install Playwright:\n"
            "  python3 -m pip install playwright\n"
            "  python3 -m playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=_BROWSER_UA)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(2500)
        html = page.content()
        browser.close()
    return html


def _blocked_by_zillow(html: str) -> bool:
    lower = html.lower()
    return (
        "px-captcha" in lower
        or "access to this page has been denied" in lower
        or "perimeterx" in lower
    )


def fetch_html(url: str) -> str:
    load_env()
    html: str | None = None
    try:
        html = _fetch_html_urllib(url)
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 429):
            raise RuntimeError(f"Could not fetch listing page (HTTP {exc.code}).") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not fetch listing page: {exc.reason}") from exc

    if html is None or _blocked_by_zillow(html):
        html = _fetch_html_playwright(url)

    if _blocked_by_zillow(html):
        raise RuntimeError(
            "Zillow blocked automated access (bot protection / captcha). "
            "Open the listing in your normal browser, copy the description into Listing text, "
            "and paste or upload 2–3 screenshots—or add this property to the ingest queue with "
            "photo URLs like the other Zillow listings."
        )
    return html


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


def _parse_zillow_html(html: str, url: str) -> dict[str, Any]:
    photo_urls: list[str] = []
    for match in _ZILLOW_PHOTO_RE.finditer(html):
        u = match.group(0)
        if u not in photo_urls:
            photo_urls.append(u)

    price: int | None = None
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
        except json.JSONDecodeError:
            pass

    if not description:
        m = re.search(r'"description"\s*:\s*"((?:\\.|[^"\\])*)"', html)
        if m:
            description = json.loads(f'"{m.group(1)}"')

    lines: list[str] = []
    if price:
        lines.append(f"List price: ${price:,}")
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

    html = fetch_html(url)
    parsed = _parse_zillow_html(html, url)
    if not parsed.get("text"):
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
