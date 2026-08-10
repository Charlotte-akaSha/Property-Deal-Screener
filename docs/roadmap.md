# Roadmap

High-level phases. **Only Phase 1–2 reflect active/local work.** Later phases are **FUTURE TARGET** unless marked complete in [current-status.md](current-status.md).

Dependencies flow downward — do not skip stabilization before migration.

---

## Phase 1 — Streamlit refactor · **MIGRATION IN PROGRESS**

**Goal:** Replace `portal.py` with multi-page Property Screener (Analyze + Compare).

| Deliverable | Status |
|-------------|--------|
| `streamlit_app.py` entry point | Local ✓ |
| `app_pages/analyze.py` | Local ✓ |
| `app_pages/compare.py` (table, map, charts, h2h, notes) | Local ✓ |
| `theme_css.py` polished UI | Local ✓ |
| Commit and push to `origin/main` | Pending |

**Depends on:** Committed pipeline (done at `15b2c83`)

---

## Phase 2 — Streamlit hardening and cleanup · **NEXT**

**Goal:** Stabilize local app; reduce doc/code drift.

- Commit UI refactor as focused changeset
- Reconcile README title vs "Property Screener" branding
- Update or archive stale sections of `BUILD_PLAN.md`
- Verify `smoke_offline.py` and `check_credentials.py` pass
- Confirm `requirements.txt` matches imports (`pandas`, `pydeck`, Altair via Streamlit)

**Depends on:** Phase 1 commit decision

---

## Phase 3 — Data/model and product stabilization · **FUTURE**

**Goal:** Trust scores and Sheet data for real acquisition decisions.

- Prompt tuning with real listings (BUILD_PLAN Phase 9)
- Validate Sheet column compatibility with existing data
- Duplicate Property ID / link handling policy (currently accepted in v1)
- Optional: warn on duplicate links

**Depends on:** Phase 2

---

## Phase 4 — Deployment preparation · **FUTURE TARGET**

**Goal:** Prepare for hosted operation (still single-user or small team).

- Choose hosting approach (not decided in repo)
- Secrets management outside `.env`
- Document production runbook
- Evaluate Streamlit Cloud vs custom deploy as interim bridge

**Depends on:** Phase 3

**Note:** Full public product deployment is Phase 8.

---

## Phase 5 — Backend/API extraction · **FUTURE TARGET**

**Goal:** Expose analysis pipeline via HTTP API; decouple from Streamlit.

- Wrap `analyze_property.py` pipeline behind API layer (stack TBD — FastAPI is a natural fit but not chosen)
- Keep `strategy.md`, prompts, schemas, `scoring.py` as shared core
- Streamlit becomes thin client or is retired

**Depends on:** Phase 4

**Migration boundary:** See [web-migration.md](web-migration.md)

---

## Phase 6 — Real web frontend · **FUTURE TARGET**

**Goal:** Polished public-facing UI replacing Streamlit.

- **Intended direction (subject to confirmation):** React/Next.js-style SPA
- Custom design system; significantly better UX than Streamlit
- Consume API from Phase 5

**Depends on:** Phase 5

---

## Phase 7 — Authentication and multi-user architecture · **FUTURE TARGET**

**Goal:** Per-user accounts and data isolation.

- Auth provider TBD
- Replace shared Sheet model with per-tenant database
- Migrate or import existing Sheet data

**Depends on:** Phase 6

---

## Phase 8 — Production deployment · **FUTURE TARGET**

**Goal:** Publicly accessible hosted application.

- Cloud infrastructure TBD
- Monitoring, error reporting, backups
- Not implemented — no deployment configs exist today

**Depends on:** Phase 7

---

## Phase 9 — Custom domain · **FUTURE TARGET**

**Goal:** Branded URL for production app.

**Depends on:** Phase 8

---

## Phase 10 — UI polish and animation · **FUTURE TARGET**

**Goal:** Professional motion and transitions on web frontend.

- **Framer Motion** — intended animation library for React/Next.js frontend
- **Not applicable** to current Streamlit app
- Stack subject to confirmation when Phase 6 begins

**Depends on:** Phase 6

---

## Phase 11 — Future enhancements · **FUTURE / OUT OF SCOPE (v1)**

From BUILD_PLAN Phase 10 — not committed:

- Auto listing scrape from URL
- Crime / climate data APIs
- Comps and market analytics
- Mobile app
- CI/CD pipeline

Re-evaluate after core web product ships.

---

## Quick reference — classification

| Phase | Label |
|-------|-------|
| 1 | **MIGRATION IN PROGRESS** |
| 2 | **CURRENT** (next) |
| 3–4 | Stabilization / prep |
| 5–10 | **FUTURE TARGET** |
| 11 | **OUT OF SCOPE** until reprioritized |
