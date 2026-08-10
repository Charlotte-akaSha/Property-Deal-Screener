# Property Screener — Documentation Index

Persistent project context for humans and AI agents. **Repository code is authoritative** when docs conflict.

> **Repository state**
>
> - **Committed baseline (`15b2c83`):** `portal.py`, analyze-only — no Compare, no `streamlit_app.py` / `app_pages/`.
> - **Local working tree (uncommitted):** `streamlit_app.py`, `app_pages/`, Compare dashboard, and related modules — **not** on a clean clone of `15b2c83`.
> - **Streamlit UI:** **CURRENT** locally; **TEMPORARY BRIDGE** architecturally.
> - If ambiguous: check `git status` and which entry-point files exist. See [current-status.md](current-status.md).

## When to read what

| Document | Read when… |
|----------|------------|
| [ai-context.md](ai-context.md) | **First** — bootstrap a new session or after context loss |
| [current-status.md](current-status.md) | Handoff, sprint planning, or checking what's done vs in progress |
| [architecture.md](architecture.md) | Changing data flow, integrations, or module boundaries |
| [product-requirements.md](product-requirements.md) | Product behavior, workflows, or acceptance criteria |
| [investment-criteria.md](investment-criteria.md) | Scoring semantics or how strategy maps to code |
| [database-schema.md](database-schema.md) | Google Sheets columns, upsert rules, local archives |
| [project-decisions.md](project-decisions.md) | Why something was built a certain way |
| [roadmap.md](roadmap.md) | Sequencing future work |
| [web-migration.md](web-migration.md) | Planning Streamlit → future web application |

## Canonical sources (do not duplicate)

| Topic | Source of truth |
|-------|-----------------|
| Investment weights, criteria, philosophy | [`strategy.md`](../strategy.md) |
| Sheet column layout | [`scripts/write_to_sheets.py`](../scripts/write_to_sheets.py) `HEADERS` |
| Extraction/scoring output shape | [`schema/`](../schema/) + [`prompts/`](../prompts/) |
| Current entry point | `streamlit_app.py` (local working tree) or `portal.py` (baseline `15b2c83`) — see banner above |

## Cursor rule

Always-applied agent instructions: [`.cursor/rules/project-documentation.mdc`](../.cursor/rules/project-documentation.mdc)
