# Columbus transit reference (for scoring — verify against official sources)

Use this when assessing **current COTA access** and **future transit investment**. Apply certainty discounts: **operating / funded / under construction** > **approved plan** > **proposed** > **feasibility study** > **conceptual**.

## Distance and corridor access

For each property, reason about:

- Walk time to the **nearest useful COTA stop** (not all stops are equal)
- Whether the parcel is within **~5–10 min walk** of a **high-value route** (e.g. Line 30, frequent trunk lines, future BRT)
- Distance to **planned** BRT/station corridors at ~0.25 / 0.5 / 1 / 2 mi

Do **not** score “Hilliard” or “Columbus” generically — distinguish **Line 30 corridor access** vs car-dependent pockets of the same suburb.

## Western Columbus — Hilliard Rome corridor (not Hilliard city)

Many listings near **Hilliard Rome Rd** (e.g. **Beacon Hill**, zip **43228**) are in the **City of Columbus**, not **Hilliard**. The street name is not the municipality — use extracted **city** / zip.

These parcels are typically **not** on **COTA Line 30** (Line 30 serves Hilliard / UA / OSU / Downtown to the north and west of this corridor). **Do not** call the property “in Hilliard” or credit **Hilliard–Downtown rapid transit**, **Leap Road LinkUS**, or **Hilliard rail station** studies as **local** catalysts unless verified very close to the parcel.

**Current transit can still be strong:** score from the **`transit` block** — e.g. **≤5 min walk** to a stop, **0-transfer** trip, **≤60 min** door-to-door Downtown often supports **current transit ~7–8/10** and **transit tier B** even without Line 30 or future BRT at the door.

**Future transit (this submarket):** without a funded station/BRT at the address, **future transit investment** and **transit appreciation** are usually **modest (~5–6/10)** — regional **COTA 2027–2031** frequency/connectivity at best, not a parcel-specific catalyst. Prefer **`Possible`** (weak) or **`None identified`** over Hilliard/Line 30 language.

## Hilliard city (Line 30 thesis)

**COTA Line 30** — **operating** (Hilliard → Upper Arlington → OSU → Downtown; direct, ~30 min headway, 7 days/week). Properties with a short walk to Line 30 stops deserve **strong current transit** scores (often **7.5–8/10**), not “suburban bus only.”

| Project | Status | Relevance |
|--------|--------|-----------|
| **COTA Line 30** | Operating | Direct Hilliard–UA–OSU–Downtown; primary current-transit driver |
| **Future Hilliard–Downtown rapid transit** | Proposed / potential | LinkUS-style rapid corridor; **not** funded like East Main BRT — score future lower than Bexley/East Main |
| **Leap Road transit-supportive infrastructure** | Funded (LinkUS) | Ped/bike access to COTA; construction ~2029 |
| **COTA 2027–2031 service expansion** | Approved plan | Frequency/connectivity uplift; not a single station |
| **Hilliard rail station** | Feasibility studied | Long-term wild card — **do not** price in as committed |

**Scoring guidance (Hilliard / Line 30 corridor, illustrative):**

- **Current transit:** 7.5–8/10 when Line 30 is a real, walkable direct connection to OSU/Downtown
- **Future transit investment:** ~7/10 — credible official rapid-transit concept + COTA investment, but Hilliard–Downtown BRT/rapid is **not** committed like **East Main BRT**
- **Transit appreciation potential:** ~7/10 — meaningful near Line 30 / Old Hilliard; do **not** treat proposed rapid transit as guaranteed

Contrast: **East Main Street BRT** (Bexley corridor) = funded/planning weight **higher** for **future** scores than Hilliard’s **proposed** rapid corridor alone.

## Other corridors (check official LinkUS / COTA sources)

| Project | Notes |
|--------|--------|
| **West Broad Street BRT** | LinkUS west side ↔ Downtown |
| **East Main Street BRT** | Downtown through Bexley, Whitehall, Reynoldsburg — **strong future catalyst when proximity is real** |
| **Northwest BRT** | Weight by funding/construction status |
| **COTA 2027–2031 Short-Range Transit Plan** | Service/frequency — not built infrastructure |

## Future transit catalyst labels

Return exactly one in `regional_assessment.future_transit_catalyst`:

- **Major catalyst** — funded/under construction or very near a station with material travel-time gain  
- **Positive** — approved/plan improvement likely to help (e.g. operating Line 30 + funded local access)  
- **Possible** — official proposed corridor (e.g. Hilliard–Downtown rapid), not firm  
- **Speculative** — feasibility / early concept only (e.g. passenger rail station study)  
- **None identified** — no credible nearby catalyst  

## `future_transit_detail` (required in Columbus scoring)

Write a **structured paragraph** the investor can read in **Details**: name each relevant project, **status** (operating / funded / proposed / study), and **what it means for this address** (walk distance, route, transfers). Mention Line 30 when the property is in Hilliard/western suburbs. Explicitly note what is **not** funded (e.g. no committed Hilliard BRT into the suburb).
