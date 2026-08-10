# Web Migration Guide

How to evolve from the **CURRENT** Streamlit Property Screener to a **FUTURE TARGET** public web application — without losing investment-analysis logic.

**Principle:** Preserve the analysis engine; replace presentation and single-user storage.

---

## What to preserve — **REUSABLE**

These are implementation-ready and should survive migration with minimal changes:

| Asset | Location | Notes |
|-------|----------|-------|
| Investment strategy | `strategy.md` | Canonical criteria + weights |
| Extraction prompt | `prompts/extraction_prompt.md` | |
| Scoring prompt | `prompts/scoring_prompt.md` | |
| JSON schemas | `schema/` | Contracts for AI output |
| Weight parsing + overall | `scripts/scoring.py` | Deterministic math |
| Analysis pipeline | `scripts/analyze_property.py` | Orchestration |
| Gemini utilities | `scripts/utils.py` | Client, retries, validation |
| Transit lookup | `scripts/transit_lookup.py` | Maps integration |
| Report generation | `scripts/reports.py` | Archive format |
| Offline tests | `scripts/smoke_offline.py` | Regression guard |

**Classification:** **CURRENT** core → **FUTURE** backend services

---

## What to replace — **TEMPORARY**

| Component | Label | Replacement |
|-----------|-------|-------------|
| `streamlit_app.py` + `app_pages/` | **TEMPORARY BRIDGE** | Web frontend (Phase 6) |
| `scripts/theme_css.py` | **TEMPORARY BRIDGE** | Frontend design system |
| `scripts/ui_helpers.py` | **TEMPORARY BRIDGE** | Frontend components |
| Google Sheets as primary DB | **TEMPORARY BRIDGE** | Relational DB + tenancy (Phase 7) |
| `scripts/sheets_data.py` | **TEMPORARY BRIDGE** | DB repository layer |
| `scripts/write_to_sheets.py` | **TEMPORARY BRIDGE** | DB write layer; optional Sheet export |
| Service account auth model | **TEMPORARY BRIDGE** | User auth (Phase 7) |
| Local-only `streamlit run` | **CURRENT** | Cloud deployment (Phase 8) |

---

## What is already legacy

| Item | Label |
|------|-------|
| `portal.py` | **LEGACY** — deleted locally; analyze logic moved to `app_pages/analyze.py` |

Do not rebuild `portal.py`. Verify migration complete before removing from git history.

---

## Future backend requirements — **FUTURE TARGET**

Not implemented. Will need:

- HTTP API wrapping `analyze_from_memory` / folder-based analyze
- Async or job queue for long Gemini + Maps calls
- Auth middleware and per-user property namespaces
- Persistent database (properties, analyses, personal notes, users)
- Object storage for photos (replace `properties/<id>/photoN.*` on disk)
- Secrets management (not committed `.env`)
- Rate limiting and API key isolation per tenant

**Stack not chosen in repository.** FastAPI or similar is a reasonable direction but remains **subject to confirmation**.

---

## Future frontend requirements — **FUTURE TARGET**

Not implemented. Will need:

- Authenticated sessions
- Analyze flow (paste, upload, region, results)
- Compare/portfolio views (filters, map, charts, notes)
- Responsive layout; accessibility
- **Animations:** Framer Motion intended for React/Next.js-style frontend — **not Streamlit**

**Stack not locked.** React/Next.js + Framer Motion is the **current intended direction**, subject to confirmation at Phase 6.

---

## Authentication — **FUTURE TARGET**

**CURRENT:** None — single user, local credentials.

**FUTURE:**

- User registration/login
- Per-user property portfolios (or org/team model TBD)
- No shared global Sheet; collaborators via app permissions

---

## Database migration — **FUTURE TARGET**

**CURRENT:** Google Sheets with regional tabs; Property ID upsert.

**Migration path (conceptual):**

1. Export Sheet rows + join with `properties/*/latest.json` for full analysis blobs
2. Map `HEADERS` columns to relational schema
3. Store analysis JSON in DB or object store
4. Retire Sheets as source of truth; optional export/sync for transition period

**Not implemented.** Keep Sheets working until migration is verified.

---

## Deployment — **FUTURE TARGET**

**CURRENT:** `streamlit run streamlit_app.py` on localhost.

**FUTURE:**

- Containerized API + static frontend
- Managed hosting (provider TBD)
- Environment-specific config (dev/staging/prod)
- Custom domain (Phase 9)

No deployment artifacts exist in the repo today.

---

## Suggested migration sequence

1. **Stabilize** Streamlit app; commit refactor (Phase 1–2)
2. **Extract** pipeline behind API; Streamlit calls API locally (Phase 5)
3. **Build** new frontend against API (Phase 6)
4. **Add** auth + database; migrate Sheet data (Phase 7)
5. **Deploy** to cloud + domain (Phase 8–9)
6. **Retire** Streamlit UI when frontend reaches parity (verify before removal)

---

## Parity checklist (before retiring Streamlit)

- [ ] Analyze: text, URL, comments, photos, region, label, results display
- [ ] Transit lookup and display
- [ ] Sheets-equivalent persistence (or DB + export)
- [ ] Compare: filters, table, map, charts, head-to-head, personal notes
- [ ] Local archive or equivalent audit trail
- [ ] CLI fallback or admin tools for batch operations
- [ ] `smoke_offline.py` equivalent for CI

---

## Do not assume exists

- REST API endpoints
- User accounts
- Production database migrations
- Framer Motion in current codebase
- Automated listing scraping
- Hosted deployment
