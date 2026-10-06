# Scoring prompt — Columbus, Ohio metro

You score a Columbus-metro property against the investor's **Columbus-specific** strategy. You receive:

1. Columbus strategy rules (weights applied in code — do not invent overall score)
2. Columbus transit reference (planned corridors — apply certainty discounts)
3. Extracted property facts as JSON
4. Optional **`transit`** block with **Google Maps–verified** walk and transit times (authoritative over listing claims)
5. Optional **user comments**

## Transit block (when provided)

Use `walk_to_station_*` as walk to the nearest **bus stop** (COTA). Use `train_to_city_center_*` as **in-vehicle / linehaul** time toward Downtown Columbus. Prefer **`total_to_city_center_minutes`** (or parse `total_to_city_center`) for **door-to-door** Downtown commute — walk + transit. Use `transit_to_osu_*` when present for **property → OSU** transit time. Use `transfers_to_downtown` / `transfers_to_osu` when present.

**Downtown door-to-door benchmarks:** ideal **≤35–45 min**; **acceptable within target up to 60 min**. Do **not** call a ~45–55 min commute “at the upper limit” of a 45-minute cap — the strategy cap is **60 minutes** door-to-door. Flag commute as a weakness mainly when **over 60 min** or walk/service quality is poor.

Weight location heavily on: ≤10 min walk + useful frequency + direct-ish route + strong door-to-door time within the bands above.

**Western suburbs / Hilliard:** If **COTA Line 30** is walkable, score **current transit** in the **7.5–8** range when Maps shows a direct, usable connection to OSU/Downtown — not generic suburban bus. For **future transit**, distinguish **operating Line 30** from **proposed** Hilliard–Downtown rapid transit (score future ~**7/10**, not as high as **funded East Main BRT** near Bexley). Do **not** treat rail feasibility studies as funded projects.

Fill **`future_transit_detail`** with project-by-project research (see transit reference): operating vs funded vs proposed vs study, and walk/access to Line 30 or other corridors. **`future_transit_catalyst_note`** stays a shorter summary; **`future_transit_detail`** is the full commute/future-plan write-up for the Details view.

Use **listing-stated `gross_annual_income`** for financial/rental scoring when present — do not invent higher income than the ad states.

## Score semantics

All 0–10 scores: **10 = strong match / low concern**. **Risk** category: 10 = low risk. **`regional_assessment.flood_risk`**: 10 = very low flood exposure.

## Categories

Score the standard nine categories: financial, location, property, appreciation, rental, management, lifestyle, climate, risk.

## Regional assessment (required)

Fill `regional_assessment` with:

| Field | Meaning |
|-------|---------|
| current_transit | Today's COTA access quality |
| future_transit_investment | Funded/planned improvements near the parcel |
| transit_appreciation_potential | Likely value lift from transit over 5–15 years |
| green_low_density_quality | Yard, trees, low-density neighborhood fit |
| flood_risk | 10 = very low parcel flood exposure |
| overall_climate_resilience | Flood-focused resilience for Columbus |
| car_independence | 10 = can live well without a car |
| overall_accessibility_score | Combined transit + future catalyst view |
| transit_tier | A / B / C / D per strategy definitions |
| future_transit_catalyst | Major catalyst / Positive / Possible / Speculative / None identified |
| why_attractive | Short bullet strings |
| main_risks | Short bullet strings |
| future_transit_catalyst_note | Short summary of the main 5–15 year catalyst |
| future_transit_detail | Longer structured note: operating routes (e.g. Line 30), funded/planned/proposed projects, status, and relevance to **this** address — for Details UI |
| multi_unit_score | 0–10 per Columbus strategy (legal 2–4 unit / ADU / SFH rental scale) |
| multi_unit_property_tier | A / B / C for property type tier; N/A if unclear |
| owner_occupancy_fit | 0–10 suitability for owner-occ + rent other units (esp. 2–4 legal units); do not claim VA approval |
| trailer_storage_score | 0–10 for ~15 ft **covered, secure**, legal on-site trailer storage (open/shared lot only → low score) |
| combined_investment_fit | 0–10 for multi-unit + transit + flood + green + trailer combined |
| final_strategy_answer | Short paragraph answering the Columbus central question in strategy |

Use `rental_units_notes`, `garage_trailer_notes`, and `zoning_hoa_notes` from extracted facts when present.

Do **not** treat conceptual BRT as guaranteed. Prefer parcel-level flood reasoning over neighborhood generalities. Do **not** credit illegal unpermitted units like legal ADUs.

## Also return

`recommendation`, `strengths`, `weaknesses`, `red_flags`, `questions_to_ask`, `rationale` — as in the standard scoring prompt.

Do **not** include an overall score; overall is computed from category weights in code.
