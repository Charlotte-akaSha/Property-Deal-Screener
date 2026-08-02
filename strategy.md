```yaml
weights:
  location: 0.24
  financial: 0.20
  appreciation: 0.15
  climate: 0.11
  rental: 0.10
  risk: 0.07
  property: 0.05
  lifestyle: 0.04
  management: 0.04
```

# Investment Property Acquisition Criteria

## Investment Goal

Buy and hold rental properties in climate-resilient, high-demand areas that offer:

* Stable rental income
* Long-term appreciation potential
* Low operational complexity
* Future optionality for personal use, relocation, or additional income streams

The ideal property is a durable asset that remains desirable across different future scenarios.

---

# What You Prioritize

## 1. Location Quality

Highest priority.

Look for:

* Strong and stable neighborhoods
* Access to major economic/cultural hubs
* Good public transportation
* Commuting distance to major cities (ideally within ~1 hour by train)
* Walkable or easy access to a train/metro station (ideally within 30 minutes walking)
* Access to services, healthcare, schools, shops, and amenities
* Areas with strong long-term demand

Preferred locations have:

* growing populations
* strong employment ecosystems
* universities, hospitals, or major employers nearby
* cultural/community activity

---

## 2. Climate Resilience

Important long-term factor.

Prefer areas with:

* Reliable water availability
* Moderate temperatures
* Lower wildfire risk
* Lower drought risk
* Lower extreme weather exposure
* Agricultural potential
* Good long-term livability

Avoid:

* Flood zones
* Coastal areas with high climate exposure
* High wildfire-risk areas
* Severe water scarcity regions

---

## 3. Property Characteristics

Preferred:

* Single-family homes, townhouses, duplexes, or properties with rental flexibility
* 2–3 bedrooms preferred
* Approximate size: **800–2,000 sqft**
* Low maintenance requirements
* Good structural condition
* Garden / green outdoor space

Strong bonuses:

* Garage and/or workshop ideally with separate entrance, storage potential, space for tools, equipment, hobbies, or business activities
* Basement, attic, or additional space that could be adapted
* Separate guest area or accessory dwelling potential
* Mature trees
* Privacy without being isolated

---

# What You Avoid

Reject properties with:

* Flood risk
* Major structural problems
* Extensive renovations required
* High crime areas
* Poor access to transportation
* Weak rental demand
* Declining population areas
* Excessive maintenance burden
* Unclear ownership/legal issues
* High insurance risk
* Lack of greenery, trees, parks, or natural surroundings

---

# Investment Philosophy

Priorities:

1. **Better location over higher yield** — A desirable location with strong long-term demand is preferred over a higher short-term return in a weaker market.

2. **Lower maintenance over maximum cash flow** — A reliable, easy-to-own property is preferred over a complicated property requiring constant management.

3. **Long-term appreciation over speculation** — Focus on durable trends: population movement, economic strength, infrastructure, climate migration, scarcity of desirable locations.

4. **Optionality matters** — Prefer properties that can adapt over time: long-term rental, personal use, guest accommodation, home office, workshop, additional rental unit.

---

# How the app scores (category mapping)

The app uses **nine category scores (0–10)**. Map your judgment as follows:

| App category | What it covers | Your framework |
|--------------|----------------|----------------|
| **location** | Neighborhood, commute, transit, walkability, amenities, demand | Location & Connectivity |
| **financial** | Price, taxes, insurance, rent, cash flow, affordability | Financial Fundamentals |
| **appreciation** | Demand drivers, supply, economic growth, desirability | Appreciation Potential |
| **climate** | Water, heat, flood, wildfire, extreme weather, habitability | Climate Resilience |
| **rental** | Tenant pool, vacancy, local rents, employment base | Rental Demand |
| **property** | Construction, condition, layout, repairs, size/bedrooms fit | Property Quality & Condition |
| **lifestyle** | Garage/workshop, ADU potential, guest space, personal-use optionality | Adaptability / Optionality |
| **management** | Remote management ease, local services, maintenance burden | Management Simplicity |
| **risk** | Flood, crime, insurance, legal clarity, declining area — **10 = low risk, 0 = high risk** | Red flags from "What You Avoid" |

**Score direction (locked):** 0 = poor match / high concern · 10 = strong match / low concern.

Weights in the YAML block at the top of this file control the overall score. Do not invent an overall score in text — it is computed in code.

---

# Recommendation labels (app output)

The app accepts exactly three recommendation values. Use this mapping from your mental categories:

| Your category | App outputs |
|---------------|-------------|
| **Strategic Buy** — strong alignment with strategy and long-term goals | `Worth visiting` |
| **Worth Visiting** — promising, needs in-person evaluation | `Worth visiting` |
| **Financial Buy** — strong numbers, weaker strategic fit | `Save` |
| **Lifestyle Buy** — personally attractive, weaker investment fundamentals | `Save` |
| **Save** — interesting but not urgent | `Save` |
| **Reject** — fails minimum criteria or major risks | `Reject` |

In `rationale`, you may name the conceptual category (e.g. "Strategic Buy") while the `recommendation` field must be one of: `Reject`, `Save`, `Worth visiting`.

---

# Category definitions (for scoring)

## Location (location)

Distance to major cities, train/metro access, walkability, employment centers, population trends, local amenities, long-term desirability.

## Financial (financial)

Purchase price, property taxes, insurance, expected rental income, cash flow potential, financing conditions, overall affordability.

## Appreciation (appreciation)

Historical appreciation, future demand drivers, limited housing supply, economic growth, area desirability.

## Climate (climate)

Water security, heat exposure, flood risk, wildfire risk, extreme weather, long-term habitability.

## Rental (rental)

Tenant pool, vacancy risk, local rental prices, employment base, transportation access.

## Property (property)

Construction quality, maintenance needs, layout, energy efficiency, immediate repair requirements, bedroom count and sqft fit (prefer 2–3 bed, 800–2,000 sqft).

## Lifestyle (lifestyle)

Garage/workshop, separate entrance, extra space, ADU potential, garden/green space, possibility of personal use.

## Management (management)

Ease of remote management, reliability of local services, maintenance requirements, tenant profile.

## Risk (risk)

Composite of flood risk, crime, insurance burden, legal/ownership clarity, declining population, major structural concerns. **10 = low risk, 0 = high risk.**
