# Database & Storage Schema

Google Sheets is the **CURRENT** shared data store and a **TEMPORARY BRIDGE** until a real database exists for the future web product.

**Authoritative column list:** `HEADERS` in [`scripts/write_to_sheets.py`](../scripts/write_to_sheets.py) — not `BUILD_PLAN.md`.

---

## Google Sheets — **CURRENT** / **TEMPORARY BRIDGE**

### Configuration

| Env var | Purpose |
|---------|---------|
| `GOOGLE_SHEETS_ID` | Spreadsheet ID |
| `GOOGLE_SHEETS_REGIONS` | Comma-separated tab names (e.g. `New York,Chicago`) |
| `GOOGLE_SHEETS_TAB` | Fallback single tab if regions unset |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Service account JSON path |

### Regional tabs

- One worksheet per region; **same column layout** on each tab
- Tab name selects region for analyze upsert and transit city-center defaults
- `sheets_data.load_properties()` concatenates all configured regions with a `Region` column

### Column layout (43 columns, in order)

| # | Header | Group | Upsert on re-analyze |
|---|--------|-------|----------------------|
| 1 | Property ID | Key | Yes |
| 2 | Link | Identification | Yes |
| 3 | City | Identification | Yes |
| 4 | State | Identification | Yes |
| 5 | Overall | Scores | Yes |
| 6 | Price | Financial | Yes |
| 7 | Price/sqft | Financial | Yes |
| 8 | Taxes | Financial | Yes |
| 9 | Estimated Insurance | Financial | Yes |
| 10 | Estimated Rent | Financial | Yes |
| 11 | House Size | Property | Yes |
| 12 | Land Size | Property | Yes |
| 13 | Bedrooms | Property | Yes |
| 14 | Bathrooms | Property | Yes |
| 15 | Walk to Station | Transit | Yes |
| 16 | Train to City Center | Transit | Yes |
| 17 | Total to City Center | Transit | Yes |
| 18 | Year Built | Property | Yes |
| 19 | Garage | Property | Yes |
| 20 | Basement | Property | Yes |
| 21 | Heating | Infrastructure | Yes |
| 22 | Cooling | Infrastructure | Yes |
| 23 | Water | Infrastructure | Yes |
| 24 | Sewer | Infrastructure | Yes |
| 25 | Internet | Infrastructure | Yes |
| 26 | Recommendation | AI | Yes |
| 27 | Strengths | AI | Yes |
| 28 | Weaknesses | AI | Yes |
| 29 | Questions to Ask | AI | Yes |
| 30 | Red Flags | AI | Yes |
| 31 | Financial | Category score | Yes |
| 32 | Location | Category score | Yes |
| 33 | Property | Category score | Yes |
| 34 | Appreciation | Category score | Yes |
| 35 | Rental | Category score | Yes |
| 36 | Management | Category score | Yes |
| 37 | Lifestyle | Category score | Yes |
| 38 | Climate | Category score | Yes |
| 39 | Risk | Category score | Yes |
| 40 | Wow Factor | **Personal** | **No** |
| 41 | Notes | **Personal** | **No** |
| 42 | Visit Date | **Personal** | **No** |
| 43 | Final Decision | **Personal** | **No** |

**Note:** There is no separate Address column; address is encoded in **Property ID** (slug from address or label). Original `.odt` spec listed Address — implementation differs.

### Extraction vs Sheets field gap

`schema/extraction_schema.json` includes **`address`** and **`status`**, which are **not** separate Sheet columns.

- **`HOA`** (monthly, from extraction `hoa`) is persisted in the **HOA** column after **Taxes**.
- `address` is reflected indirectly via Property ID slug; `status` lives in extraction JSON / local `analysis_*.json` only.

### Upsert behavior

- **Key:** Property ID (column A)
- **Append** if new ID; **update** if exists
- **Update range:** columns 1 through `UPDATABLE_COUNT` (39) — all except personal columns
- **Personal columns** left unchanged on update; blank on append
- Headers rewritten if row 1 missing or mismatched

### Internal load metadata (not in Sheet)

Added by `sheets_data.load_region()`:

| Column | Purpose |
|--------|---------|
| `Region` | Source tab name |
| `_sheet_row` | 1-based row number for write-back |

---

## Derived metrics — **CURRENT** (Compare UI only)

Computed in `sheets_data.add_derived_columns()` — **not persisted** to Sheet:

| Column | Formula / source |
|--------|------------------|
| `Commute (min)` | Parsed from `Total to City Center` text |
| `Gross yield %` | `(Estimated Rent × 12 / Price) × 100` |
| `Net monthly` | `Rent − Taxes/12 − Insurance/12` |
| `Score profile` | List of nine category scores (for charts) |

Currency strings in Sheet (e.g. `$425,000`) coerced via `to_number()`.

---

## Local property archive — **CURRENT**

Path: `properties/<Property_ID>/` (gitignored)

| Artifact | Description |
|----------|-------------|
| `listing.txt` | URL + listing text |
| `user_comments.txt` | Optional investor notes |
| `photo1.*` … `photo5.*` | Screenshots |
| `analysis_<timestamp>.json` | Immutable per-run snapshot |
| `report_<timestamp>.md` | Human-readable report |
| `latest.json` | Most recent analysis (plain copy) |

### Analysis JSON shape (summary)

```json
{
  "extracted": { "...": "extraction_schema fields" },
  "scored": {
    "categories": { "financial": 7.5, "...": 0 },
    "overall": 8.4,
    "overall_computed_from_weights": true,
    "recommendation": "Worth visiting",
    "strengths": [], "weaknesses": [], "red_flags": [], "questions_to_ask": [],
    "rationale": ""
  },
  "transit": { "walk_to_station": "...", "...": "..." },
  "meta": {
    "property_id": "...",
    "analyzed_at": "ISO8601",
    "model": "gemini-...",
    "prompt_version": "extraction_v1 / scoring_v1",
    "sheet_tab": "New York"
  }
}
```

---

## Geocode cache — **CURRENT**

Path: `.cache/geocode.json` (gitignored)

```json
{
  "Property_ID_slug": [latitude, longitude]
}
```

- Populated by `scripts/geocode.py` on demand for Compare map
- Address resolved from `latest.json` extracted fields, else slug as fallback
- Delete file to force re-geocode

---

## Thumbnails — **CURRENT**

Path: `static/property_thumbs/<Property_ID>.jpg` (gitignored)

- Generated from first `photoN.*` in property folder via `scripts/photos.py`
- Served by Streamlit static hosting (`enableStaticServing = true` in `.streamlit/config.toml`)
- Regenerated when source photo is newer

---

## Future storage — **FUTURE TARGET**

For the public web product:

- Replace Sheets with relational DB + per-user tenancy
- Object storage for photos and analysis archives
- Migration path from Sheet export — not implemented

See [web-migration.md](web-migration.md).
