"""One-off: set listing agent fields (and optional contingent flag) for known Zillow URLs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from contacted import add_contingent  # noqa: E402
from listing_from_url import import_from_url  # noqa: E402
from sheets_data import (  # noqa: E402
    property_id_for_link_substring,
    save_listing_agent_fields,
)
from write_to_sheets import list_regions, open_worksheet  # noqa: E402

LISTINGS: list[dict[str, str]] = [
    {
        "zpid": "33953663",
        "url": "https://www.zillow.com/homedetails/920-Ferndale-Pl-Columbus-OH-43209/33953663_zpid/",
        "region": "Columbus",
    },
    {
        "zpid": "2079401811",
        "url": "https://www.zillow.com/homedetails/126-E-6th-Ave-126-Columbus-OH-43201/2079401811_zpid/",
        "region": "Columbus",
        "name": "Nader Akrouche",
        "company": "RE/MAX Connection Realtors",
        "phone": "(614) 477-2443",
    },
    {
        "zpid": "2124115869",
        "url": "https://www.zillow.com/homedetails/2211-N-4th-St-Columbus-OH-43201/2124115869_zpid/",
        "region": "Columbus",
        "name": "Nader Akrouche",
        "company": "RE/MAX Connection Realtors",
        "phone": "(614) 477-2443",
        "contingent": "1",
    },
]


def _apply_agent(
    region: str,
    property_id: str,
    *,
    name: str,
    company: str,
    phone: str,
) -> None:
    save_listing_agent_fields(
        property_id,
        region,
        name=name,
        company=company,
        phone=phone,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch listing agent columns on Google Sheets")
    parser.add_argument(
        "--fetch-zillow",
        action="store_true",
        help="Import agent from Zillow when not set in LISTINGS",
    )
    args = parser.parse_args()
    regions = list_regions()
    default_region = "Columbus" if "Columbus" in regions else (regions[0] if regions else "Columbus")

    for item in LISTINGS:
        region = item.get("region") or default_region
        zpid = item["zpid"]
        ws = open_worksheet(region)
        pid = property_id_for_link_substring(ws, zpid)
        if not pid:
            print(f"SKIP  no row with zpid {zpid} on {region}", flush=True)
            continue

        name = item.get("name", "").strip()
        company = item.get("company", "").strip()
        phone = item.get("phone", "").strip()

        if args.fetch_zillow and (not name or not phone):
            try:
                imported = import_from_url(item["url"])
                name = name or str(imported.get("listing_agent_name") or "").strip()
                company = company or str(imported.get("listing_agent_company") or "").strip()
                phone = phone or str(imported.get("listing_agent_phone") or "").strip()
            except Exception as exc:  # noqa: BLE001
                print(f"WARN  Zillow import for {zpid}: {exc}", flush=True)

        if not name and not company and not phone:
            print(f"SKIP  no agent data for {pid}", flush=True)
            continue

        _apply_agent(region, pid, name=name, company=company, phone=phone)
        print(f"OK    {pid}: {name} | {company} | {phone}", flush=True)

        if item.get("contingent"):
            add_contingent(pid)
            print("      marked contingent", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
