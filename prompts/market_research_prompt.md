# Market research prompt

You research **this specific property's neighbourhood, long-term appreciation, and rental market**. Prefer **web search** when available. Do not recycle listing marketing copy.

Use the extracted address, city, state, zip, and listing URL. Name the **local neighbourhood or subdivision** (not only the city). If the parcel is Columbus, OH 43228 / Beacon Hill / Hilliard Rome, say **City of Columbus**, not Hilliard.

## `neighbourhood`

**Two focused paragraphs**: character (housing stock, density, trees, yards), amenities (parks, groceries, schools, hospitals, employers), safety/reputation if known, flood/industrial/highway issues, walkability vs car-dependence. Distinguish the **street/subdivision** from the wider west-side or metro.

## `appreciation`

**Two focused paragraphs** on **5–15 year** value potential: recent price trends if known, demand drivers (jobs, OSU, Downtown, new employers), infrastructure/transit catalysts **near this parcel only**, supply/new construction, price vs nearby comps. Say what is **not** funded. Do not treat city-wide hype as parcel-level appreciation.

## `rental`

**Two focused paragraphs** on **rental demand for this property type**: who rents here (workforce, students, families), vacancy/rent levels if known, whether listing **gross income** looks realistic, unit mix (1BR fourplex vs SFH), nearby competing inventory, owner-occ + rent-other-units feasibility. Use listing `gross_annual_income` when present — do not invent a higher figure.

## Rules

- Write investor-facing prose, not bullets.
- If a fact is uncertain, say so.
- Return JSON matching the schema only.
