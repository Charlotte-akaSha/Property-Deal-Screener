# AI Real Estate Acquisition Assistant

Local Streamlit portal that extracts facts from a listing (text + up to 5 screenshots), scores the property against your investment strategy with Gemini, saves a timestamped local archive, and upserts a row into a shared Google Sheet.

## Setup

1. **Clone** this repo to a local (non-iCloud) path for day-to-day work.
2. Create a virtualenv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Copy env template and fill in secrets:

```bash
cp .env.example .env
```

4. **Gemini:** create an API key and set `GEMINI_API_KEY`. Optionally set `GEMINI_MODEL` (default `gemini-3.6-flash`). Multimodal calls cost more than text-only; the portal caps uploads at **5 images**.
5. **Google Maps (transit columns):**
   - In the same Google Cloud project, enable **Geocoding**, **Places**, **Distance Matrix**, and **Directions** APIs.
   - Create or reuse an API key; set `GOOGLE_MAPS_API_KEY` in `.env`.
   - On each analysis, the app geocodes the address, finds the nearest train/transit station, and computes:
     - **Walk to Station** — walking time/distance (not from the listing)
     - **Train to City Center** — transit time from that station to the regional hub (New York → Grand Central; Chicago → Millennium Station)
   - Override hubs per tab with `CITY_CENTER_NEW_YORK` / `CITY_CENTER_CHICAGO` in `.env` if needed.
6. **Google Sheet:**
   - Create a spreadsheet; note the ID from the URL.
   - Add one tab per region (e.g. **New York**, **Chicago**) — same columns on each tab.
   - Set `GOOGLE_SHEETS_REGIONS=New York,Chicago` in `.env` (comma-separated tab names).
   - In Google Cloud: enable Google Sheets API, create a service account, download JSON to `credentials/service_account.json`.
   - Share the spreadsheet with the service account email as **Editor**.
   - Set `GOOGLE_SHEETS_ID` in `.env`.
   - Headers are created automatically on first write if a tab is empty.
   - If you already have data, insert two columns after **State**: **Walk to Station**, **Train to City Center** (or clear row 1 and re-run — the app will rewrite headers).

7. Run the app:

```bash
streamlit run streamlit_app.py
```

Use **Analyze** to score a new listing; use **Compare** to filter, map, chart, and compare every property in your Google Sheet (and edit Wow Factor, Notes, Visit Date, Final Decision).

The **Map** tab plots each property using `GOOGLE_MAPS_API_KEY`. Coordinates are cached in `.cache/geocode.json`, so each address is geocoded only once — delete that file to force a refresh.

## CLI

```bash
# Folder must already contain listing.txt (+ optional photoN.*)
# --region is required when GOOGLE_SHEETS_REGIONS has multiple tabs
python scripts/analyze_property.py properties/Some_Property_Slug --region "New York"
python scripts/analyze_property.py properties/Some_Property_Slug --skip-sheets --region "New York"
python scripts/write_to_sheets.py properties/Some_Property_Slug
```

## What is shared where

| System | Role |
|--------|------|
| GitHub | Code, prompts, strategy — not property data |
| Google Sheets | Shared property database (rankings, notes) |
| Local `properties/` | Listing archives, photos, timestamped analyses (gitignored) |

Pasting the same listing twice with different labels can create two Property IDs in v1.

## Credentials check

```bash
python scripts/check_credentials.py
```

## Offline smoke test

```bash
python scripts/smoke_offline.py
```

This validates strategy weights, JSON schemas, local file writers, and Sheet row mapping without calling Gemini or Google Sheets.
