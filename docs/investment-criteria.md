# Investment Criteria — Implementation Guide

## Canonical source

**[`strategy.md`](../strategy.md)** is the single source of truth for:

- Category weights (YAML block at top)
- Investment goal and philosophy
- Location, climate, property, and rejection criteria
- Category definitions and recommendation mapping
- Score semantics

**Do not duplicate weights or full criteria here.** Edit `strategy.md` when investment philosophy changes.

---

## How code implements the strategy

### Weight parsing — `scripts/scoring.py`

1. Reads `strategy.md`
2. Extracts fenced ` ```yaml ` block at the top
3. Validates all nine categories present and weights sum to **1.0** (±0.001)
4. Fails fast on missing/invalid weights

### Category scoring — Gemini + prompts

1. `strategy_rules_without_weights()` strips the YAML block; human-readable rules go to the model
2. `prompts/scoring_prompt.md` enforces score semantics and transit authority
3. `schema/scoring_schema.json` constrains output shape
4. Gemini returns nine category scores (0–10) plus recommendation and narrative fields
5. Gemini does **not** return an overall score

### Overall score — Python only

```text
overall = round(sum(category_score × weight), 2)
```

Implemented in `scoring.compute_overall()`. Flag `overall_computed_from_weights: true` in analysis JSON.

**The LLM never directly calculates the weighted overall score.**

---

## Nine weighted categories

Fixed set in `scoring.CATEGORIES`:

`financial`, `location`, `property`, `appreciation`, `rental`, `management`, `lifestyle`, `climate`, `risk`

Each maps to a section in `strategy.md` (see "How the app scores" table there).

**Exact weights:** read the YAML block in `strategy.md` — do not maintain a second weight table in docs.

---

## Score semantics (locked)

| Value | Meaning |
|-------|---------|
| **0** | Poor match / high concern |
| **10** | Strong match / low concern |

**Risk category:** measures risk *quality* for the investment — **10 = low risk**, **0 = high risk**.

Enforced in `scoring_prompt.md` and validated as 0–10 in `scoring.py`.

---

## Recommendations

Schema allows exactly:

- `Reject`
- `Save`
- `Worth visiting`

Mapping from investor mental models is documented in `strategy.md` ("Recommendation labels").

---

## Transit and location scoring

When Google Maps transit data is available:

- Injected into scoring payload as `transit` object
- `scoring_prompt.md` treats transit times as **authoritative** over listing claims
- Location scoring should weight walk ≤ ~30 min and reasonable train commute per strategy

---

## Extraction estimates

`prompts/extraction_prompt.md` instructs Gemini to **ballpark** `estimated_rent` (monthly) and `estimated_insurance` (annual) when the listing omits them. These are estimates, not verified facts — used for financial scoring and Compare yield metrics.

---

## Implementation notes / deviations

| Topic | Detail |
|-------|--------|
| Original `.odt` spec | Simpler early weights; current `strategy.md` is evolved and authoritative |
| `BUILD_PLAN.md` example weights | Differ from current `strategy.md` — use `strategy.md` |
| No hard-coded auto-reject rules | Rejection flows through AI recommendation, not Python thresholds |
| Re-analyze | Updates scores and AI fields; personal Sheet columns untouched |
| Duplicate listings | Same listing + different label → two Property IDs (v1 accepted behavior) |

---

## Related files

| File | Role |
|------|------|
| `strategy.md` | Criteria + weights |
| `prompts/scoring_prompt.md` | Scoring instructions |
| `prompts/extraction_prompt.md` | Fact extraction (no scoring) |
| `schema/scoring_schema.json` | Output contract |
| `scripts/scoring.py` | Weights + overall computation |
