"""Re-align regional tabs after agent headers were inserted without shifting row data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from sheet_row_decode import decode_physical_row  # noqa: E402
from write_to_sheets import (  # noqa: E402
    HEADERS,
    _listing_agent_cell,
    ensure_headers,
    list_regions,
    open_worksheet,
)


def _encoded_row(legacy: dict[str, str], *, name: str, company: str, phone: str) -> list[str]:
    listing_agent = _listing_agent_cell(
        {
            "listing_agent_name": name,
            "listing_agent_company": company,
            "listing_agent_phone": phone,
        }
    )
    out: list[str] = []
    for header in HEADERS:
        if header == "Listing agent":
            out.append(listing_agent)
        elif header == "Agent phone":
            out.append(phone)
        else:
            out.append(legacy.get(header, ""))
    return out


def repair_region(region: str, *, dry_run: bool) -> int:
    ws = open_worksheet(region)
    values = ws.get_all_values()
    if not values:
        print(f"{region}: empty tab", flush=True)
        return 0

    fixed: list[list[str]] = [HEADERS]
    for physical in values[1:]:
        if not any(str(c).strip() for c in physical):
            continue
        legacy, name, company, phone = decode_physical_row(physical)
        if not legacy.get("Property ID"):
            continue
        fixed.append(_encoded_row(legacy, name=name, company=company, phone=phone))

    print(f"{region}: {len(fixed) - 1} data rows -> {len(HEADERS)} columns", flush=True)
    if dry_run:
        sample = fixed[1] if len(fixed) > 1 else []
        if sample:
            pid = sample[0]
            print(
                f"  sample {pid}: City={sample[HEADERS.index('City')]} "
                f"Price={sample[HEADERS.index('Price')]} "
                f"Rec={sample[HEADERS.index('Recommendation')][:40]} "
                f"Hood={sample[HEADERS.index('Neighbourhood')][:40]}",
                flush=True,
            )
        return len(fixed) - 1

    ensure_headers(ws)
    ws.clear()
    ws.update(range_name="A1", values=fixed, value_input_option="USER_ENTERED")
    return len(fixed) - 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair sheet rows after agent header mismatch")
    parser.add_argument(
        "--region",
        action="append",
        help="Tab to repair (default: Columbus if present)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    regions = args.region or []
    if not regions:
        available = list_regions()
        regions = ["Columbus"] if "Columbus" in available else available[:1]
    if not regions:
        print("No regions configured.", file=sys.stderr)
        return 1
    for region in regions:
        repair_region(region, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
