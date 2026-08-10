# Project Decisions (ADR-style)

Recorded decisions evident from repository history and code. **Dates and owners are not documented in the repo** unless noted from git commits.

Format: **Status** · **Decision** · **Context** · **Consequences**

---

## ADR-001: Streamlit for v1 local application

**Status:** **CURRENT**

**Decision:** Use Streamlit as the local UI for property analysis.

**Context:** BUILD_PLAN Phase 3; rapid single-user portal. Originally `portal.py`; locally refactored to `streamlit_app.py` + `app_pages/`.

**Consequences:** Fast iteration; limited polish vs custom frontend. UI refactor in progress uncommitted.

---

## ADR-002: Google Gemini for extraction and scoring

**Status:** **CURRENT**

**Decision:** Use Google Gemini (`google-genai`) for multimodal extraction and category scoring.

**Context:** Initial scaffold (`1befca5`); default model updated to `gemini-3.6-flash` (`e1c4e0b`).

**Consequences:** Requires `GEMINI_API_KEY`; multimodal calls cost more; 5-photo cap.

---

## ADR-003: Google Sheets as single-user shared database

**Status:** **CURRENT** / **TEMPORARY BRIDGE**

**Decision:** Google Sheets is the shared property database, accessed via service account.

**Context:** BUILD_PLAN "portal-first, Sheets as database"; collaborators share via Sheet link without running software.

**Consequences:** Works for one investor + collaborators; not suitable for multi-tenant product without redesign.

---

## ADR-004: Manual listing input — no scraping in v1

**Status:** **CURRENT**

**Decision:** Users paste listing text; URL is stored but not scraped.

**Context:** BUILD_PLAN Phase 10 explicitly excludes auto Zillow scrape. Original `.odt` spec mentioned "paste Zillow link directly" as aspiration — not implemented.

**Consequences:** Reliable, ToS-safe ingestion; more user effort per property.

---

## ADR-005: Python computes weighted overall score

**Status:** **CURRENT**

**Decision:** Gemini scores nine categories only; `scoring.py` computes overall from `strategy.md` weights.

**Context:** BUILD_PLAN Phase 2 "category score semantics locked"; prevents LLM weight drift.

**Consequences:** Deterministic overall; weights editable in `strategy.md` without prompt changes.

---

## ADR-006: JSON Schema validation with one retry

**Status:** **CURRENT**

**Decision:** Validate extraction and scoring output against `schema/*.json`; retry once with error feedback.

**Context:** BUILD_PLAN architecture diagram.

**Consequences:** Higher reliability; failed validation writes nothing.

---

## ADR-007: Property ID upsert with personal column preservation

**Status:** **CURRENT**

**Decision:** Upsert on Property ID; on update, overwrite analysis columns but preserve Wow Factor, Notes, Visit Date, Final Decision.

**Context:** BUILD_PLAN Phase 7.

**Consequences:** Safe re-analysis; personal visit workflow intact.

---

## ADR-008: Regional Sheet tabs

**Status:** **CURRENT**

**Decision:** Multiple worksheet tabs per region (`GOOGLE_SHEETS_REGIONS`) with identical columns.

**Context:** Commit `e1c4e0b` — expanded from single Properties tab in original plan.

**Consequences:** Region selects transit hub defaults and upsert target.

---

## ADR-009: Google Maps for verified transit

**Status:** **CURRENT**

**Decision:** Compute walk-to-station and train-to-city-center via Google Maps APIs; pass to scorer as authoritative.

**Context:** Commit `15b2c83`; README documents required APIs.

**Consequences:** Requires `GOOGLE_MAPS_API_KEY`; location scoring uses real commute data.

---

## ADR-010: Compare dashboard as current product scope

**Status:** **CURRENT** (local) / **ALREADY MIGRATED** beyond BUILD_PLAN

**Decision:** Build a full Compare dashboard (filter, map, charts, head-to-head, notes) as part of the Streamlit app.

**Context:** `BUILD_PLAN.md` Phase 10 listed "portfolio dashboard" as out of scope; implemented in uncommitted `app_pages/compare.py`.

**Consequences:** Product scope expanded; significant uncommitted UI work.

---

## ADR-011: Local timestamped archives

**Status:** **CURRENT**

**Decision:** Every successful analysis writes immutable timestamped JSON/Markdown plus `latest.json` under `properties/`.

**Context:** BUILD_PLAN Phase 6; Sheets failure must not lose data.

**Consequences:** Disk usage grows; full audit trail per property.

---

## ADR-012: Future migration to proper web application

**Status:** **FUTURE TARGET**

**Decision:** Eventually replace Streamlit with a polished web frontend, API/backend separation, authentication, real database, cloud deployment, and custom domain.

**Context:** User direction; BUILD_PLAN Phase 10 lists cloud hosting and multi-user auth as out of scope for v1.

**Consequences:** Current architecture is a bridge; see [web-migration.md](web-migration.md).

**Frontend direction (subject to confirmation):** React/Next.js-style SPA with Framer Motion for animations — not chosen in repository code.

---

## ADR-013: GitHub for code only — not property data

**Status:** **CURRENT**

**Decision:** Commit code, prompts, strategy; gitignore `properties/`, `.env`, `credentials/`.

**Context:** README "What is shared where"; BUILD_PLAN §1.2.

**Consequences:** Property data lives locally + in shared Sheet.

---

## Rejected / deferred (from BUILD_PLAN Phase 10)

| Item | Status |
|------|--------|
| Auto Zillow scrape | **OUT OF SCOPE** |
| Crime/climate APIs | **OUT OF SCOPE** |
| Comps engine | **OUT OF SCOPE** |
| GitHub Actions CI | **OUT OF SCOPE** |
| Cloud hosting (v1) | **OUT OF SCOPE** → **FUTURE TARGET** |
