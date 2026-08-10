# AI Context — Property Screener

**Bootstrap document.** Read this first, then drill into linked docs as needed.

> **Repository state**
>
> - **Committed baseline (`15b2c83`):** entry point is `portal.py`; analyze-only. No Compare, no `streamlit_app.py`, no `app_pages/`, no `sheets_data.py` / `geocode.py` / `photos.py` / `theme_css.py`.
> - **Local working tree (uncommitted):** Streamlit multi-page refactor — `streamlit_app.py`, `app_pages/`, Compare dashboard, supporting modules above; `portal.py` deleted locally.
> - A **clean clone of `15b2c83` does not include the refactor.** Do not assume Compare or `streamlit_app.py` exist without checking.
> - **Streamlit UI:** **CURRENT** in the local working tree; **TEMPORARY BRIDGE** architecturally (target is a proper web app). Both labels apply — not contradictory.
> - If ambiguous: run `git status` and inspect which entry-point files exist before assuming which UI is available.

## What it is

**Property Screener** is a local, single-user tool for rental property acquisition analysis. Users paste listing text and screenshots; the app extracts facts with Gemini, scores against a personal investment strategy, computes transit via Google Maps, archives results locally, and upserts rows into a shared Google Sheet. In the **local working tree**, a **Compare** dashboard filters, maps, charts, and edits personal notes across the portfolio (not present at baseline `15b2c83`).

UI title: **Property Screener**. README title: *AI Real Estate Acquisition Assistant*. GitHub repo: `Property-Deal-Screener`.

## Current purpose

Help one investor screen buy-and-hold rental properties: fast structured analysis, ranked portfolio view, and shared Sheet for collaboration — without building a public product yet.

## Current architecture (summary)

*Local working tree only — see Repository state banner above.*

```
streamlit_app.py → app_pages/{analyze,compare}.py → scripts/* → Gemini / Maps / Sheets
                                              ↓
                              properties/<id>/ + .cache/geocode.json
```

At baseline `15b2c83`: `portal.py` → `analyze_from_memory` → same `scripts/*` pipeline (no Compare).

## Entry point

**Local working tree:**

```bash
streamlit run streamlit_app.py
```

**Committed baseline (`15b2c83`):**

```bash
streamlit run portal.py
```

`portal.py` is **LEGACY** relative to the local refactor — deleted locally; still present at `15b2c83`.

## Current stack

| Layer | Technology |
|-------|------------|
| UI | Streamlit ≥1.40 (`st.navigation`, top tabs) |
| Language | Python 3 |
| AI | Google Gemini (`google-genai`, default `gemini-3.6-flash`) |
| Validation | `jsonschema` + one retry |
| Strategy weights | YAML in `strategy.md` → `scoring.py` |
| Data store | Google Sheets (`gspread`) — **TEMPORARY BRIDGE** |
| Maps/transit | Google Maps APIs |
| Charts/map | Altair (via Streamlit), pydeck |

No authentication, no REST API, no production deployment.

## Major integrations

- **Gemini** — multimodal extraction + category scoring
- **Google Maps** — geocode, nearest rail station, walk + transit commute
- **Google Sheets** — regional tabs, upsert by Property ID

## Migration state

| Item | Label |
|------|-------|
| Core pipeline (`analyze_property.py`, scoring, prompts) | **CURRENT** (committed) |
| `portal.py` single-page UI | **LEGACY** |
| `streamlit_app.py` + Compare dashboard | **MIGRATION IN PROGRESS** (uncommitted) |
| Google Sheets as DB | **TEMPORARY BRIDGE** |
| React/Next.js + Framer Motion web app | **FUTURE TARGET** |

## Source-of-truth files

- `strategy.md` — investment criteria and weights
- `scripts/write_to_sheets.py` — Sheet schema
- `scripts/analyze_property.py` — analysis pipeline
- `prompts/`, `schema/` — AI contracts
- `streamlit_app.py` — UI entry (local working tree)

## Blockers

- Substantial UI refactor not committed; `origin/main` does not include Compare dashboard or new entry point
- `BUILD_PLAN.md` still references `portal.py` and marks dashboard out of scope
- Repo path is iCloud Drive (README warns this can cause git friction)

## Immediate next steps

1. Finish and commit the Streamlit refactor when ready (do not mix with unrelated work)
2. Align `BUILD_PLAN.md` / README naming with **Property Screener**
3. Run `python scripts/smoke_offline.py` after schema or pipeline changes

## Future web-app direction

Separate **analysis engine** (Python, reusable) from **presentation** (polished web frontend, auth, real database, cloud hosting, custom domain). Intended frontend direction: React/Next.js-style app with Framer Motion for animations — **FUTURE TARGET**, not implemented.

See [web-migration.md](web-migration.md) and [roadmap.md](roadmap.md).

## Agent rule

Follow [`.cursor/rules/project-documentation.mdc`](../.cursor/rules/project-documentation.mdc).
