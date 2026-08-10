# Architecture

> **Repository state**
>
> - **Committed baseline (`15b2c83`):** `portal.py`, analyze-only. No Compare, no `streamlit_app.py` / `app_pages/` / `sheets_data.py` / `geocode.py` / `photos.py` / `theme_css.py`.
> - **Local working tree (uncommitted):** multi-page refactor with `streamlit_app.py`, `app_pages/`, Compare, and modules above; `portal.py` deleted locally.
> - **Not on a clean clone of `15b2c83`.** Inspect `git status` and files on disk when ambiguous.
> - **Streamlit UI:** **CURRENT** locally; **TEMPORARY BRIDGE** toward the future web app.

## Current architecture — **CURRENT** (local working tree)

*Diagram below describes the **local uncommitted** UI. Baseline `15b2c83` uses `portal.py` (analyze-only) into the same `scripts/` pipeline.*

Local single-user Streamlit application. No API layer, no authentication, no cloud deployment.

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (localhost:8501)                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    streamlit_app.py          ← entry point
                    theme_css.inject()
                    st.navigation (top tabs)
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
     app_pages/analyze.py          app_pages/compare.py
              │                             │
              │ analyze_from_memory         │ sheets_data.load_properties
              ▼                             │ geocode, photos, pydeck, altair
     scripts/analyze_property.py            ▼
              │
    ┌─────────┼─────────┬──────────────┐
    ▼         ▼         ▼              ▼
 extract   transit   score        persist_local
 (Gemini)  (Maps)   (Gemini +    (reports.py)
                     scoring.py)
              │
              ▼
     write_to_sheets.py → Google Sheets (regional tabs)
              │
              ▼
     properties/<Property_ID>/   (local archive, gitignored)
       listing.txt, photoN.*, user_comments.txt
       analysis_<ts>.json, report_<ts>.md, latest.json
```

### Entry point

**`streamlit_app.py`** — sets page config, injects CSS, runs `st.navigation` with **Analyze** and **Compare**.

`portal.py` — **LEGACY** (deleted locally; existed at commit `15b2c83`).

### UI pages (`app_pages/`)

| Page | File | Role |
|------|------|------|
| Analyze | `analyze.py` | Form: URL, text, comments, photos (max 5), region, label → run pipeline → show results |
| Compare | `compare.py` | Load Sheet data, sidebar filters, KPIs, tabs: table, map, charts, head-to-head, personal notes |

**Status:** **MIGRATION IN PROGRESS** (uncommitted). Committed baseline only had `portal.py` (analyze-only).

### Core scripts (`scripts/`)

| Module | Role |
|--------|------|
| `analyze_property.py` | Pipeline: extract → transit → slug → folder → score → local → Sheets |
| `scoring.py` | Parse `strategy.md` weights; compute weighted overall |
| `utils.py` | Gemini client, schemas, prompts, slugs, retries |
| `transit_lookup.py` | Google Maps geocode, nearest rail station, walk + transit times |
| `write_to_sheets.py` | Sheet upsert by Property ID; preserve personal columns |
| `reports.py` | Timestamped JSON + Markdown + `latest.json` |
| `sheets_data.py` | Read Sheet → pandas; derived metrics; save personal edits |
| `geocode.py` | Lat/lon for map; disk cache |
| `photos.py` | Thumbnails from archived `photoN.*` |
| `theme_css.py` | Custom Streamlit styling |
| `ui_helpers.py` | Formatting and score display |
| `check_credentials.py` | Env + Sheets auth check |
| `smoke_offline.py` | Offline validation (no API calls) |

### External services

| Service | Use |
|---------|-----|
| **Google Gemini** | Multimodal extraction + category scoring |
| **Google Maps** | Geocoding, Places, Distance Matrix, Directions |
| **Google Sheets** | Shared property database (**TEMPORARY BRIDGE**) |

### Local storage

| Path | Contents | Git |
|------|----------|-----|
| `properties/<Property_ID>/` | Listing, photos, analyses | Ignored |
| `.cache/geocode.json` | Property ID → [lat, lon] | Ignored |
| `static/property_thumbs/` | JPEG thumbnails for compare table | Ignored |
| `credentials/service_account.json` | Sheets service account | Ignored |
| `.env` | API keys | Ignored |

### Data flow — Analyze

1. User submits listing text (+ optional URL, comments, ≤5 images, region)
2. **Gemini** extracts facts → JSON schema validation (retry once)
3. **Google Maps** computes walk-to-station and train-to-city-center (Monday 8 AM benchmark)
4. Property ID slug created; folder written under `properties/`
5. **Gemini** scores nine categories vs `strategy.md` rules (+ transit JSON)
6. **`scoring.py`** computes weighted overall (not LLM)
7. **`reports.py`** writes timestamped local files
8. **`write_to_sheets.py`** upserts row; personal columns preserved on update

Sheets failure does not delete local archive.

### Data flow — Compare

1. **`sheets_data.load_properties`** reads all configured regional tabs
2. Derived columns: commute minutes, gross yield %, net monthly
3. Filters, KPIs, visualizations; personal notes written back via **`save_personal_edits`**
4. Map uses **`geocode.coordinates_for`** (cached); thumbnails from **`photos.ensure_thumbnail`**

### Authentication — **CURRENT**

None. Single-user tool. Secrets in local `.env` and `credentials/`. Sheet access via service account shared on the spreadsheet.

### Deployment — **CURRENT**

Local only: `streamlit run streamlit_app.py`. No Streamlit Cloud, Docker, or CI configs found.

---

## Future target architecture — **FUTURE TARGET**

Not implemented. Conceptual target for a public product:

```
┌──────────────┐     ┌──────────────┐     ┌─────────────────────────┐
│   Frontend   │────▶│  API layer   │────▶│  Analysis services      │
│  (polished   │     │  (auth,      │     │  (extract, score,       │
│   web UI)    │     │   tenancy)   │     │   transit — Python)     │
└──────────────┘     └──────────────┘     └───────────┬─────────────┘
                                                      │
                                                      ▼
                                          ┌───────────────────────┐
                                          │ Persistent database   │
                                          │ (+ object storage for │
                                          │  photos/archives)     │
                                          └───────────────────────┘
```

**Intended direction (subject to confirmation):**

- **Frontend:** React/Next.js-style SPA with polished UX
- **Animations:** Framer Motion — **FUTURE TARGET** (not applicable to Streamlit)
- **Backend:** Extract existing Python pipeline behind HTTP API (e.g. FastAPI — not chosen in repo)
- **Auth:** User accounts, per-tenant data isolation
- **Database:** Replace Google Sheets as primary store for multi-user product
- **Deployment:** Cloud hosting + custom domain

See [web-migration.md](web-migration.md).
