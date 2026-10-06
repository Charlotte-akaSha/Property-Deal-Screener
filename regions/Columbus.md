```yaml
weights:
  location: 0.26
  climate: 0.14
  appreciation: 0.14
  financial: 0.14
  rental: 0.14
  risk: 0.08
  property: 0.05
  lifestyle: 0.03
  management: 0.02
```

# Columbus, Ohio metro — investment criteria

When analyzing a property in the **Columbus, Ohio metro**, give **transit accessibility, future transit investment, and flood/climate risk very high weight**. The objective is not simply to find a pleasant house, but to identify properties likely to remain desirable and appreciate because of accessibility, infrastructure investment, and climate resilience.

**Ideal price band:** approximately **$300k–$400k** detached house with yard, mature trees, low flood risk, ≤10–15 minute walk to useful COTA service, **ideally ≤35–45 minutes door-to-door to Downtown by transit** (acceptable up to **60 minutes**), good OSU connectivity, and a credible future transit catalyst within ~0.5–1 mile when possible.

## Current public transit (COTA)

**Downtown commute target (door-to-door):** use Google Maps `total_to_city_center` when provided — walk to stop **plus** transit ride(s). **Ideal ≤35–45 min**; **still within target up to 60 min**. Only treat commute as a meaningful weakness when **over 60 min** door-to-door (or walk to useful COTA is poor).

Weight **≤10-minute walk + frequent service + direct route + ≤35-minute trip to Downtown** far above a property with a nearby but infrequent bus or multiple transfers.

Evaluate walking distance/time to the nearest COTA stop, routes within 5/10/15-minute walks, weekday peak/daytime/evening/weekend frequency, 7-day service, and direct connections to Downtown Columbus, OSU, major employers, hospitals, and cultural areas. Estimate transit time to Downtown and OSU and count transfers.

Classify nearest transit tier:

- **Tier A:** BRT/rapid, high frequency, major hub, rail-equivalent
- **Tier B:** frequent regular COTA bus, direct to Downtown/OSU, ~≤10 min walk
- **Tier C:** regular bus but lower frequency or transfer required
- **Tier D:** infrequent, long walk, weak evenings/weekends, car-dependent

Do **not** treat all bus stops as equal.

## Future transit investment

Search and reason about **official** COTA, LinkUS, MORPC, and City of Columbus plans. Distinguish certainty levels (highest weight first):

1. Existing service  
2. Under construction  
3. Fully funded/approved  
4. Advanced design/planning  
5. Officially identified future corridor  
6. Conceptual/proposed only  

Never present speculative lines as guaranteed. See `regions/columbus_transit_reference.md` for corridors to check (West Broad BRT, East Main BRT, Northwest BRT, Line 30 Hilliard–UA–OSU–Downtown, COTA 2027–2031 plan themes).

Score proximity at ~0.25 / 0.5 / 1 / 2 miles to high-quality existing or planned corridors.

## Green / low-density preference

**Not downtown.** Prioritize: detached house + private yard/garden + trees + low-density neighborhood + useful transit ≤10–15 min walk + **ideally ≤35–45 min** (acceptable **≤60 min** door-to-door) to Downtown by transit + OSU access. Do not auto-favor dense urban cores.

## Flood risk (parcel-level)

Major negative. Use **parcel-level** analysis: FEMA zone, Columbus/Franklin County flood GIS, rivers/creeks/ravines, drainage, access-road flooding, insurance implications. A green river-adjacent lot is **not** automatically positive.

Flood-risk scale (for `regional_assessment.flood_risk`, 10 = very low risk):

- **9–10:** outside floodplain, strong separation from waterways  
- **7–8:** outside floodplain, minor drainage concerns  
- **5–6:** moderate nearby exposure, house reasonably protected  
- **3–4:** close to floodplain/creek/ravine  
- **1–2:** in significant flood zone or recurring flooding  

For Columbus, weight **flood/drainage** much more than wildfire.

## Multi-unit / rental strategy (income-producing investment)

Prioritize **legal** income-producing configurations. Do **not** treat unpermitted basement/ADU as equal to legal units.

**Property type tiers**

- **Tier A:** duplex, triplex, fourplex, legal multi-family, house with **legal** ADU  
- **Tier B:** large SFH with credible **legal** ADU potential, detached structure with conversion potential, separate entrance + kitchen/bath potential  
- **Tier C:** standard SFH with strong rental fundamentals only  

When possible, assess: legal unit count, beds per unit, current/estimated market rent per unit, separate utilities/meters, entrances, kitchens, occupancy, zoning, permitted configuration, ADU/multi-family feasibility, gross rent, opex, NOI, gross yield, owner-occupancy layout.

### Owner-occupancy / VA loan consideration

Flag **2–4 legal units** where one unit could be owner-occupied and others rented (do **not** assert VA approval — only structural suitability).

**Multi-unit score (`regional_assessment.multi_unit_score`)**

- **10:** legal 2–4 unit, strong demand, good owner-occ layout, attractive rent vs price  
- **8:** legal ADU or strong legal ADU potential  
- **6:** large house with credible additional-unit potential  
- **4:** ordinary SFH rental  
- **0–3:** hard to rent separately / restrictive  

## Trailer storage / covered garage (~15 ft travel trailer)

Major requirement: store a **small (~15 ft) travel trailer** on-site, **covered and secure**, without off-site storage.

Prefer: large detached garage, oversized door height/width/depth, covered carport, legal RV/trailer parking, deep side driveway, rear/side maneuvering room. **Open shared parking lots do not count** as covered or secure trailer storage.

Judge from listing/photos (not sqft alone): door width/height, depth, driveway width, turning radius, side-yard/gate access, slope, obstacles, whether trailer can be backed in.

Check zoning/HOA: RV/trailer parking, outdoor storage, garage storage, new carport feasibility.

**Trailer score (`regional_assessment.trailer_storage_score`)**

- **10:** large covered garage/RV structure, sufficient size, easy access, legal, good maneuvering  
- **8:** covered carport or very large garage with minor limits  
- **6:** on-property but exposed or awkward  
- **3:** possible but restricted / difficult access  
- **0:** no practical legal storage  

Reject regardless of other merits if **serious flood risk**, **major structural concern**, or **impossible trailer/storage**.

## Combined preference & search priority

Ideal combo: **multi-unit + green neighborhood + yard + current/future transit + low flood + trailer storage**.

When comparing similar properties, prioritize:

1. Legal multi-unit / rental income potential  
2. Low flood and climate risk  
3. Current + future transit  
4. Price vs rental income  
5. Green neighborhood / yard / QoL  
6. Covered trailer storage  
7. Long-term appreciation  
8. Aesthetic appeal  

## Central question

> Would this be a good property for us to buy with an owner-occupancy strategy, generate rental income from multiple units, keep our trailer securely on the property, live in a green neighborhood without being completely car-dependent, and benefit from Columbus's future transit investment?
