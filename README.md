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

4. **Gemini:** create an API key and set `GEMINI_API_KEY`. Optionally set `GEMINI_MODEL` (default `gemini-2.5-flash`). Multimodal calls cost more than text-only; the portal caps uploads at **5 images**.
5. **Google Sheet:**
   - Create a spreadsheet; note the ID from the URL.
   - In Google Cloud: enable Google Sheets API, create a service account, download JSON to `credentials/service_account.json`.
   - Share the spreadsheet with the service account email as **Editor**.
   - Set `GOOGLE_SHEETS_ID` in `.env`.
   - Headers are created automatically on first write if the sheet is empty.

6. Run the portal:

```bash
streamlit run portal.py
```

## CLI

```bash
# Folder must already contain listing.txt (+ optional photoN.*)
python scripts/analyze_property.py properties/Some_Property_Slug
python scripts/analyze_property.py properties/Some_Property_Slug --skip-sheets
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
