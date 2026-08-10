# Product Requirements

What the application **actually does today**, based on code, README, `strategy.md`, `BUILD_PLAN.md`, and the original `.odt` spec. Where docs conflict, **code wins**.

**Labels:** **CURRENT** = implemented; **OUT OF SCOPE** = explicitly not built.

---

## Product summary — **CURRENT**

Property Screener helps a rental-property investor:

1. Analyze listings from pasted text and screenshots
2. Score properties against a weighted personal strategy
3. Store results in a shared Google Sheet and local archive
4. **Compare** and rank the portfolio with filters, map, charts, and personal notes — **local working tree only** (uncommitted Streamlit refactor); **not** in committed baseline `15b2c83`

Target user time per analysis: under ~2 minutes (excluding API latency) — per BUILD_PLAN.

---

## Analyze workflow — **CURRENT**

**Page:** `app_pages/analyze.py` (local) / `portal.py` (committed baseline)

### Inputs

| Field | Required | Notes |
|-------|----------|-------|
| Listing text | Yes | Primary source; no auto-scrape |
| Listing URL | No | Stored as metadata only — **OUT OF SCOPE:** URL scraping |
| User comments | No | Included in extraction and scoring |
| Photos | No | Max 5 images (png, jpg, webp, gif) |
| Property label override | No | Replaces address-derived Property ID |
| Region (Sheet tab) | Yes when multiple regions | e.g. New York, Chicago |

### Processing

1. Gemini multimodal **extraction** → `extraction_schema.json`
2. Google Maps **transit lookup** (walk to nearest rail station + train to regional hub)
3. Property ID slug → `properties/<id>/` folder created
4. Gemini **scoring** → nine category scores + recommendation + narrative fields
5. Python **weighted overall** via `scoring.py`
6. Local timestamped archive + `latest.json`
7. Google Sheets upsert (personal columns preserved on re-analyze)

### Outputs (on screen)

- Match score, recommendation, category scores
- Price, estimated rent, estimated insurance
- Transit summary (when Maps key configured)
- Strengths, weaknesses, red flags, questions, rationale
- Sheet link or distinct failure message if Sheets write fails

### Failure behavior

Pipeline order (`analyze_from_memory`):

1. Gemini extraction
2. Transit lookup
3. `save_listing_inputs()` — creates `properties/<id>/`, writes `listing.txt` / photos / comments
4. Gemini scoring
5. `persist_local()` — writes `analysis_*.json`, `report_*.md`, `latest.json`
6. Google Sheets upsert

What gets written on failure:

- **Extraction fails** (after retry) → no property folder; no analysis files; no Sheet row.
- **Transit fails before step 3** → same — nothing from the property persistence stage.
- **Scoring fails after step 3** → property folder **may exist** with listing inputs only; **no** `analysis_*.json`, `report_*.md`, `latest.json`, or Sheet row. Do **not** describe this as “nothing written.”
- **Sheets upsert fails after step 5** → local analysis archive saved; retry via CLI `write_to_sheets.py`

---

## Compare workflow — **CURRENT** (local uncommitted)

**Page:** `app_pages/compare.py`

**Note:** Original `BUILD_PLAN.md` Phase 10 listed portfolio dashboard as **OUT OF SCOPE**. The Compare dashboard is **real current work** — **ALREADY MIGRATED** beyond the original plan.

### Features

- Load all properties from configured regional Sheet tabs
- **Sidebar filters:** regions, price range, min match score, max commute, min bedrooms, recommendation verdicts
- **KPI row:** count, avg match, best match, etc.
- **Tabs:**
  - **Compare** — HTML table with thumbnails, verdict pills, property detail dialog
  - **Map** — pydeck scatter; click for detail; geocode cache
  - **Charts** — Altair distributions and score breakdowns
  - **Head-to-head** — compare 2–4 properties side by side
  - **My notes** — edit Wow Factor, Notes, Visit Date, Final Decision → write back to Sheet

### Derived metrics (Compare only, not stored in Sheet)

- **Gross yield %** = `(Estimated Rent × 12) / Price × 100`
- **Net monthly** = `Rent − Taxes/12 − Insurance/12`
- **Commute (min)** parsed from Total to City Center text

---

## Scoring — **CURRENT**

- **Nine categories:** financial, location, property, appreciation, rental, management, lifestyle, climate, risk
- **Semantics:** 0 = poor match / high concern; 10 = strong match / low concern
- **Risk:** 10 = low risk, 0 = high risk
- **Weights:** YAML block at top of `strategy.md` — see [investment-criteria.md](investment-criteria.md)
- **Overall score:** computed in Python only (`scoring.py`); LLM must not output overall
- **Recommendations:** exactly one of `Reject`, `Save`, `Worth visiting`

---

## Transit calculations — **CURRENT**

Via `transit_lookup.py` + Google Maps APIs:

- Geocode property address
- Find nearest **rail** station (train/subway; bus stops excluded)
- **Walk to station** — walking duration/distance
- **Train to city center** — transit from station to regional hub, **Monday 8:00 AM** local
- **Total to city center** — walk + train
- Default hubs: Grand Central (New York), Millennium Station (Chicago); overridable via `.env`

Transit data is passed to Gemini for location scoring and stored in Sheet columns.

---

## Personal notes — **CURRENT**

Four **personal columns** on the Sheet (never overwritten by re-analyze):

| Column | Compare UI |
|--------|------------|
| Wow Factor | Numeric (notes tab) |
| Notes | Text |
| Visit Date | Date |
| Final Decision | Select: Pursue, Maybe, Pass, Visited, Offer made |

---

## Google Sheets persistence — **CURRENT** / **TEMPORARY BRIDGE**

- One spreadsheet; **one tab per region** (`GOOGLE_SHEETS_REGIONS`)
- Upsert keyed on **Property ID** (column A)
- Headers auto-written on empty tab
- Shared with collaborators via normal Google Sheet sharing

See [database-schema.md](database-schema.md).

---

## Local archives — **CURRENT**

Per property under `properties/<Property_ID>/`:

| File | Purpose |
|------|---------|
| `listing.txt` | URL (line 1 if present) + pasted text |
| `user_comments.txt` | Optional investor notes |
| `photo1.*` … `photo5.*` | Uploaded screenshots |
| `analysis_<timestamp>.json` | Full analysis (never overwritten) |
| `report_<timestamp>.md` | Human-readable report |
| `latest.json` | Copy of most recent run |

---

## Ingestion model — **CURRENT**

**Manual paste only.** User copies listing text from Zillow or elsewhere.

| Capability | Status |
|------------|--------|
| Paste listing text | **CURRENT** |
| Upload screenshots | **CURRENT** (max 5) |
| Store listing URL | **CURRENT** (metadata) |
| Auto-scrape from URL | **OUT OF SCOPE** (original spec aspired to this; not built) |
| Zillow API / comps | **OUT OF SCOPE** |
| Crime / climate APIs | **OUT OF SCOPE** |
| Duplicate-link warning | **OUT OF SCOPE** (v1 accepts duplicate Property IDs) |

---

## CLI — **CURRENT**

```bash
python scripts/analyze_property.py properties/<slug> --region "New York"
python scripts/write_to_sheets.py properties/<slug>
python scripts/check_credentials.py
python scripts/smoke_offline.py
```

---

## Non-requirements (do not assume)

- User authentication or multi-tenant isolation
- Production hosting or custom domain
- REST API
- Automated listing import
- Mobile app
- CI/CD pipeline

These are **FUTURE TARGET** items — see [roadmap.md](roadmap.md).
