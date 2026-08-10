# Current Status — Living Handoff

Last verified against repository: **2026-08-09**

## Git baseline (committed)

| Field | Value |
|-------|-------|
| Branch | `main` (tracks `origin/main`) |
| HEAD | `15b2c83e3874d31eec5ade5e5fefd98014e2fb9d` |
| Latest commit message | Add transit lookup, rent/insurance estimates, and clearer portal results. |
| Total commits | 3 |
| Remote | `https://github.com/Charlotte-akaSha/Property-Deal-Screener.git` |

### What the committed baseline includes

- Core analysis pipeline: `scripts/analyze_property.py`, `scoring.py`, `utils.py`, `reports.py`, `write_to_sheets.py`, `transit_lookup.py`
- `portal.py` as Streamlit entry (single-page analyze UI)
- Regional Sheet tabs, transit columns, Gemini 3.6 default
- `strategy.md`, prompts, schemas, `fixtures/`, `BUILD_PLAN.md`, `README.md`

### What the committed baseline does **not** include

- `streamlit_app.py` multi-page navigation
- `app_pages/analyze.py` and `app_pages/compare.py`
- Compare dashboard (table, map, charts, head-to-head, notes)
- `scripts/theme_css.py`, `sheets_data.py`, `geocode.py`, `photos.py`, `ui_helpers.py`
- `.streamlit/config.toml` theme config

---

## Working tree (local, uncommitted)

**Label: MIGRATION IN PROGRESS** — treat this as the actual runnable app locally.

### Modified (vs HEAD)

| File | Change |
|------|--------|
| `.gitignore` | Adds `.cache/`, `static/property_thumbs/` |
| `README.md` | Updated for `streamlit_app.py`, Compare page, map cache |
| `portal.py` | **Deleted** |
| `requirements.txt` | Adds `pandas`, `pydeck` |
| `scripts/smoke_offline.py` | Extended offline tests (imports `sheets_data` — see below) |
| `scripts/transit_lookup.py` | Minor updates |

### Untracked (new local work)

| Path | Role |
|------|------|
| `streamlit_app.py` | **CURRENT** entry point |
| `app_pages/analyze.py` | Analyze page |
| `app_pages/compare.py` | Compare dashboard |
| `scripts/theme_css.py` | Custom UI/CSS |
| `scripts/sheets_data.py` | Load Sheet → DataFrame, derived metrics, personal edits |
| `scripts/geocode.py` | Map geocoding cache |
| `scripts/photos.py` | Property thumbnails |
| `scripts/ui_helpers.py` | Display helpers |
| `.streamlit/config.toml` | Theme + static serving |
| `docs/` | Project documentation system (complete locally, uncommitted) |
| `.cursor/rules/project-documentation.mdc` | Always-applied Cursor documentation rule |
| `.agents/`, `.claude/` | Symlinks to Streamlit package skill (not project-specific) |

**`smoke_offline.py` tree difference:** At baseline `15b2c83`, the script ends with `streamlit run portal.py` and does **not** import `sheets_data.py`. The local modified version imports and tests `sheets_data` derived columns. A clean checkout of `15b2c83` cannot run the extended smoke tests until uncommitted `sheets_data.py` (and related files) are present.

**Do not commit** `keys ect....odt` — potentially sensitive, untracked.

---

## What is complete

| Area | Status |
|------|--------|
| Extract → score → local archive → Sheets upsert | **CURRENT** — working (committed pipeline) |
| Transit lookup (walk + train to city hub) | **CURRENT** — committed |
| Weighted overall score in Python | **CURRENT** — committed |
| Regional Sheet tabs | **CURRENT** — committed |
| Analyze page (new UI) | **MIGRATION IN PROGRESS** — local only |
| Compare dashboard | **MIGRATION IN PROGRESS** — local only; **ALREADY MIGRATED** beyond original BUILD_PLAN scope |
| Map + geocode cache | **MIGRATION IN PROGRESS** — local only |
| Photo thumbnails in compare table | **MIGRATION IN PROGRESS** — local only |
| Documentation system (`docs/`, `.cursor/`) | **Complete locally** — uncommitted; pending first commit |
| Production deployment | **Not started** |
| Public API / auth / real database | **FUTURE TARGET** |

Local data: **9** property folders under `properties/` (gitignored).

---

## In progress

1. **Streamlit UI refactor** — multi-page app, SaaS-style theme, Compare dashboard
2. **First commit** of documentation system and UI refactor (both present locally, neither on `origin/main`)
3. Commit/push decision for UI refactor (pending user)

---

## Blocked / risks

- Large drift between `origin/main` and local working tree
- Documentation drift: `BUILD_PLAN.md` references `portal.py`, single Properties tab, dashboard out of scope
- iCloud repo path may cause sync/git issues

---

## Known documentation drift

| Doc | Issue |
|-----|-------|
| `BUILD_PLAN.md` | Entry `portal.py`; Phase 10 excludes portfolio dashboard; older column list |
| `README.md` | Partially updated locally; title still "AI Real Estate Acquisition Assistant" |
| Original `.odt` spec | Single "Properties" tab; mentions future Zillow paste (not implemented) |

Code wins over stale docs. See [product-requirements.md](product-requirements.md).

---

## Immediate next steps

1. Test Analyze + Compare flows locally (`streamlit run streamlit_app.py`)
2. When ready: commit UI refactor as a focused changeset
3. Update `BUILD_PLAN.md` or supersede with [roadmap.md](roadmap.md)
4. Keep [current-status.md](current-status.md) updated after meaningful milestones
