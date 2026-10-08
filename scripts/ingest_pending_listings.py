"""Run analysis + Sheets upsert for queued Zillow listings."""

from __future__ import annotations

import argparse
import ssl
import sys
import urllib.request
from pathlib import Path
from typing import Any

import certifi

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from analyze_property import analyze_from_memory
from utils import analysis_backend

LISTINGS: list[dict[str, Any]] = [
    {
        "name": "Grove City duplex",
        "link": "https://www.zillow.com/homedetails/3610-3612th-Grv-Grove-City-OH-43123/465465662_zpid/",
        "photo_urls": [
            "https://photos.zillowstatic.com/fp/1eb84f215b86c2559ad36d662b432355-cc_ft_960.jpg",
            "https://photos.zillowstatic.com/fp/2d53641412a82a5bbe36ff0fbdc1c972-cc_ft_960.jpg",
            "https://photos.zillowstatic.com/fp/3b0e487ee50f54bb4502bedce6c6293e-cc_ft_960.jpg",
        ],
        "text": """
3610 3612th Grv, Grove City, OH 43123
MLS #226036004
List price: $419,900
Property type: MultiFamily / Duplex
Year built: 1900 (major remodel 2026 per area comps context)

OWNER FINANCING AVAILABLE! Updated duplex in Downtown Grove City. Each unit: 2 bed, 1.5 bath.
Updates: fresh paint, LVP flooring, lighting, tile kitchen floors, new stair carpet, stainless appliances, vinyl windows.
Fully permitted mechanical updates. Fresh landscaping. Minutes from Historic Downtown Grove City and Downtown Columbus.

Lot size: 10,018 sqft | Parcel: 040000231
Heating: Forced Air | Cooling: Central Air
Sewer: Public | Water: Public
Annual tax: $4,096 | On market: 9/21/2026
Listing terms: Owner Financing
Walk Score: 71 | Bike Score: 62
Agents: Oscar Martinez Mejia, Taylor Matthews — Howard Hanna
""".strip(),
    },
    {
        "name": "Blossom Ave duplex",
        "link": "https://www.zillow.com/homedetails/2673-2675-Blossom-Ave-Columbus-OH-43231/33934633_zpid/",
        "photo_urls": [
            "https://photos.zillowstatic.com/fp/5a81a4f0bc898133ef1ebb89d730cabf-cc_ft_960.jpg",
            "https://photos.zillowstatic.com/fp/e96a91af8d701a873a6a7910f9ed6a3a-cc_ft_960.jpg",
            "https://photos.zillowstatic.com/fp/2eaa742dbd4342ddddc89902f1507bd2-cc_ft_960.jpg",
        ],
        "text": """
2673-2675 Blossom Ave, Columbus, OH 43231
MLS #226036971
List price: $385,000
Duplex | Year built: 1977
Townhouse/ranch units; attached garage; partially finished basement.

Unit 2673: 3 bed townhouse 1.5 bath with garage/basement.
Unit 2675: 2 bed ranch 1.5 bath with garage/basement.
Tenants pay utilities (water sub-metered), mowing/snow removal.
Leased through 12/31/2026 — Unit 2673 $1,050/mo, Unit 2675 $1,607/mo.
Gross rent roughly $2,657/mo ($31,884/yr) from listing.
Near Mount Carmel St. Ann's, JPMorgan Chase, Uptown Westerville, Easton.
Lot: 9,147 sqft | Annual tax: $4,591
Tenant occupied — curb offers only.
""".strip(),
    },
    {
        "name": "Kirkersville 3-plex",
        "link": "https://www.zillow.com/homedetails/321-N-5th-St-Kirkersville-OH-43033/114207295_zpid/",
        "photo_urls": [
            "https://photos.zillowstatic.com/fp/f36857206f6b7356f51f618779435553-cc_ft_960.jpg",
            "https://photos.zillowstatic.com/fp/cec0f59f29233928a523ce4cde88c357-cc_ft_960.jpg",
            "https://photos.zillowstatic.com/fp/7c855eeb7bd4b2a40309492cf910e99f-cc_ft_960.jpg",
        ],
        "text": """
321 N 5th St, Kirkersville, OH 43033
MLS #226021671
List price: $310,000
Property type: MultiFamily — 3-unit (fully occupied)
Year built: 1970

Fully occupied 3-plex with immediate rental income. Landlord pays trash, sewer, mowing, minimal common electric (well pump, garage lighting).
Three residential units, each with private back deck and large shared backyard.
Largest unit: 6 bed, 2 full bath, private driveway.
Two smaller units: 3 bed each; one 2 full bath, one 1 full bath; shared parking area.
Two exterior-access storage units (extra income). 1.5-car garage.
Annual tax: $3,138
""".strip(),
    },
    {
        "name": "Whitethorne Ave duplex",
        "link": "https://www.zillow.com/homedetails/141-Whitethorne-Ave-Columbus-OH-43223/33853457_zpid/",
        "photo_urls": [
            "https://photos.zillowstatic.com/fp/d600492a4f9e852618acf93a3ba56eea-cc_ft_960.jpg",
            "https://photos.zillowstatic.com/fp/98315924b65ea6cd7fe0ed3491ade8c5-cc_ft_960.jpg",
            "https://photos.zillowstatic.com/fp/98a01fe75da05d61d1ea9d9a4f1bdf8e-cc_ft_960.jpg",
        ],
        "text": """
141 Whitethorne Ave, Columbus, OH 43223
MLS #311727
List price: $179,900
Multi Family duplex | Year built: 1925
4 beds | 2 baths | 1,604 sqft living area
Zestimate: $174,800 | $112/sqft

Description:
Duplex with high ceilings and original wood details. Upstairs: carpeted 2-bed 1-bath with kitchenette.
Downstairs: 2-bed 1-bath with hardwood floors and full kitchen. Huge rooms; extra storage/closets.
Recent improvements: new main water line and meter, updated electric panel/outlets, new gutters and roof over back porch, new drywall and paint.
Basement water remediation and front wheelchair ramp coming soon. All appliances convey.
Historic Hilltop, Columbus City Schools. Off-street parking; near highways and bus; bikeable to downtown.
Curb offers only; both units on long-term lease.

Facts:
- Basement: Unfinished | Cooling: None | Heating: See Remarks
- Parking: Off Street, On Street
- Parcel: 01004889600 | Lot dimensions: 41 x 131
- Sewer/Water: Public
- Annual tax: $1,785 | Assessed value: $110,900
- On market: 9/25/2026 | Terms: 1031 Exchange, Cash, Conventional
- Agent: Chastity Butterfield-Contini (419-296-1909), Hartsock Realty
""".strip(),
    },
]


def _download_photos(urls: list[str]) -> list[tuple[str, bytes]]:
    ctx = ssl.create_default_context(cafile=certifi.where())
    uploads: list[tuple[str, bytes]] = []
    for i, url in enumerate(urls, start=1):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                data = resp.read()
        except Exception as exc:  # noqa: BLE001
            print(f"  skip photo {i}: {exc}", flush=True)
            continue
        uploads.append((f"photo{i}.jpg", data))
    return uploads


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest queued Zillow listings")
    parser.add_argument(
        "--only",
        help="Run a single queue entry by name substring (e.g. Whitethorne)",
    )
    args = parser.parse_args()
    backend = analysis_backend()
    print(f"Analysis backend: {backend}", flush=True)
    queue = LISTINGS
    if args.only:
        key = args.only.lower()
        queue = [x for x in LISTINGS if key in x["name"].lower()]
        if not queue:
            print(f"No listing matches --only={args.only!r}", flush=True)
            return 1
    failures = 0
    for item in queue:
        print(f"\n=== {item['name']} ===", flush=True)
        uploads = _download_photos(item["photo_urls"])
        print(f"  photos: {len(uploads)}", flush=True)

        def progress(msg: str) -> None:
            print(f"  … {msg}", flush=True)

        try:
            result = analyze_from_memory(
                item["text"],
                link=item["link"],
                image_uploads=uploads or None,
                progress=progress,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED: {exc}", flush=True)
            failures += 1
            continue
        scored = result["analysis"]["scored"]
        print(f"  Property ID: {result['analysis']['meta']['property_id']}")
        print(f"  Overall: {scored['overall']} — {scored['recommendation']}")
        if result.get("sheets_error"):
            print(f"  SHEETS ERROR: {result['sheets_error']}")
            failures += 1
        elif result.get("sheets"):
            s = result["sheets"]
            print(f"  Sheets {s['action']} on {s.get('sheet_tab')}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
