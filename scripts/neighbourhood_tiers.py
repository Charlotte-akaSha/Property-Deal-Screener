"""Columbus-area search tiers, colours, and area-level appreciation / rental notes."""

from __future__ import annotations

import re
from dataclasses import dataclass

PRIORITY = 1       # Dark green — excellent rental + appreciation
STRONG = 2         # Light green — strong rental + appreciation
SELECTIVE = 3      # Yellow — moderate rental + appreciation
OPPORTUNISTIC = 4  # Orange — mixed / specialized
LOW = 5            # Red — weak rental + appreciation

RULES_VERSION = 14

# Qualitative rental / appreciation bands, stored as /10 for the table.
_VERY_HIGH = 9.5
_HIGH = 8.5
_MED_HIGH = 7.5
_MEDIUM = 6.5
_LOW_MED = 5.0
_LOW_SCORE = 4.0

# (tier, substring, appreciation /10, rental /10) — first match wins.
# Colour is rental + appreciation only. Flood is a separate column.
_PROFILES: tuple[tuple[int, str, float, float], ...] = (
    # More specific names before the areas they sit inside
    (OPPORTUNISTIC, "west franklinton", _HIGH, _HIGH),
    (OPPORTUNISTIC, "central hilltop", _HIGH, _HIGH),
    # Strong appreciation, but flood exposure keeps the colour off green.
    (OPPORTUNISTIC, "franklinton", _VERY_HIGH, _HIGH),
    (OPPORTUNISTIC, "the bottoms", _VERY_HIGH, _HIGH),
    (PRIORITY, "weinland park", _HIGH, _HIGH),
    (PRIORITY, "italian village", _HIGH, _HIGH),
    (PRIORITY, "victorian village", _HIGH, _HIGH),
    (STRONG, "old north", _MED_HIGH, _HIGH),
    (STRONG, "olde towne east", _HIGH, _HIGH),
    (STRONG, "merion village", _HIGH, _HIGH),
    (STRONG, "bexley", _HIGH, _MEDIUM),
    (STRONG, "upper arlington", _HIGH, _MEDIUM),
    (STRONG, "new albany", _HIGH, _MEDIUM),
    (STRONG, "berwick", _MED_HIGH, _MEDIUM),
    (SELECTIVE, "whitehall", _MEDIUM, _HIGH),
    (SELECTIVE, "westgate", _MED_HIGH, _MEDIUM),
    (SELECTIVE, "near east", _MEDIUM, _HIGH),
    (SELECTIVE, "east columbus", _MEDIUM, _HIGH),
    (SELECTIVE, "king-lincoln", _MED_HIGH, _HIGH),
    (SELECTIVE, "bronzeville", _MED_HIGH, _HIGH),
    (SELECTIVE, "eastmoor", _MED_HIGH, _MEDIUM),
    (SELECTIVE, "clintonville", _HIGH, _HIGH),
    (SELECTIVE, "old beechwold", _HIGH, _MEDIUM),
    (SELECTIVE, "beechwold", _HIGH, _MEDIUM),
    (SELECTIVE, "grandview", _HIGH, _MEDIUM),
    (SELECTIVE, "fifth by northwest", _MED_HIGH, _HIGH),
    (SELECTIVE, "university district", _MEDIUM, _VERY_HIGH),
    (SELECTIVE, "dublin", _HIGH, _MEDIUM),
    (SELECTIVE, "worthington", _HIGH, _MEDIUM),
    (SELECTIVE, "hilliard", _MED_HIGH, _MEDIUM),
    (SELECTIVE, "grove city", _MEDIUM, _MED_HIGH),
    (SELECTIVE, "hilltop", _MEDIUM, _MED_HIGH),
    (OPPORTUNISTIC, "franklin park", _MEDIUM, _MEDIUM),
    (OPPORTUNISTIC, "driving park", _MEDIUM, _HIGH),
    (OPPORTUNISTIC, "southern orchards", _MEDIUM, _HIGH),
    (OPPORTUNISTIC, "hungarian village", _MEDIUM, _HIGH),
    (OPPORTUNISTIC, "milo-grogan", _MEDIUM, _HIGH),
    (OPPORTUNISTIC, "linden", _MEDIUM, _HIGH),
    (SELECTIVE, "woodland park", _MEDIUM, _MEDIUM),
    (OPPORTUNISTIC, "eastgate", _MEDIUM, _MEDIUM),
    (OPPORTUNISTIC, "reynoldsburg", _MEDIUM, _MEDIUM),
    (OPPORTUNISTIC, "gahanna", _MED_HIGH, _MEDIUM),
    (OPPORTUNISTIC, "westerville", _HIGH, _MEDIUM),
    (LOW, "obetz", _LOW_MED, _MEDIUM),
    (LOW, "groveport", _LOW_MED, _MEDIUM),
    (LOW, "canal winchester", _LOW_MED, _MEDIUM),
    (LOW, "north central", _LOW_MED, _MEDIUM),
    (LOW, "shepard", _LOW_MED, _MEDIUM),
    (LOW, "shepherd", _LOW_MED, _MEDIUM),
    # Outside this Columbus ranking
    (LOW, "port jervis", _LOW_SCORE, _LOW_MED),
    (LOW, "croton-on-hudson", _LOW_SCORE, _LOW_MED),
    (LOW, "ossining", _LOW_SCORE, _LOW_MED),
    (LOW, "lake peekskill", _LOW_SCORE, _LOW_MED),
    (LOW, "montrose", _LOW_SCORE, _LOW_MED),
    (LOW, "cortlandt manor", _LOW_SCORE, _LOW_MED),
    (SELECTIVE, "valleyview", _MEDIUM, _MEDIUM),
    (SELECTIVE, "lincoln village", _MEDIUM, _MED_HIGH),
    (OPPORTUNISTIC, "lancaster", _MEDIUM, _HIGH),
    (OPPORTUNISTIC, "kirkersville", _LOW_SCORE, _VERY_HIGH),
    (OPPORTUNISTIC, "galloway", _MEDIUM, _MEDIUM),
    (OPPORTUNISTIC, "westland", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "georgesville", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "trabue", _MEDIUM, _MEDIUM),
    (OPPORTUNISTIC, "far west", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "west columbus", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "far east", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "far south", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "southwest columbus", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "south columbus", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "southeast columbus", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "northeast columbus", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "northland", _LOW_MED, _MEDIUM),
    (OPPORTUNISTIC, "pickerington", _MEDIUM, _MEDIUM),
)


@dataclass(frozen=True)
class NeighbourhoodProfile:
    tier: int
    appreciation: float
    rental: float


def _norm(label: object) -> str:
    text = re.sub(r"\s+", " ", str(label or "").strip().lower())
    return text.replace("—", "").strip()


def resolve_neighbourhood_profile(label: object) -> NeighbourhoodProfile | None:
    hay = _norm(label)
    if not hay or hay in ("nan", "none", "columbus", "columbus, oh"):
        return None
    for tier, needle, appreciation, rental in _PROFILES:
        if needle in hay:
            return NeighbourhoodProfile(tier, appreciation, rental)
    return None


def neighbourhood_search_tier(label: object) -> int | None:
    profile = resolve_neighbourhood_profile(label)
    return profile.tier if profile else None


def score_note_10(value: float) -> str:
    return f"{value:g}/10"


def area_appreciation_note(label: object) -> str | None:
    profile = resolve_neighbourhood_profile(label)
    return score_note_10(profile.appreciation) if profile else None


def area_rental_note(label: object) -> str | None:
    profile = resolve_neighbourhood_profile(label)
    return score_note_10(profile.rental) if profile else None


def tier_emoji(tier: int | None) -> str:
    return {
        PRIORITY: "🟢",
        STRONG: "🟢",
        SELECTIVE: "🟡",
        OPPORTUNISTIC: "🟠",
        LOW: "🔴",
    }.get(tier or 0, "")


def tier_short_label(tier: int | None) -> str:
    return {
        PRIORITY: "Excellent rental + appreciation",
        STRONG: "Strong rental + appreciation",
        SELECTIVE: "Moderate rental + appreciation",
        OPPORTUNISTIC: "Mixed opportunity",
        LOW: "Weak rental + appreciation",
    }.get(tier or 0, "")


def _band_label(value: float) -> str:
    if value >= 9.2:
        return "very high"
    if value >= 8.2:
        return "high"
    if value >= 7.2:
        return "medium-high"
    if value >= 6.2:
        return "medium"
    if value >= 4.7:
        return "low-medium"
    return "low"


# Written evaluation for the neighbourhood popup. First matching needle wins, same order as _PROFILES.
_EVALUATIONS: dict[str, str] = {
    "west franklinton": (
        "West Franklinton and Central Hilltop have strong redevelopment potential, with high rental demand "
        "and high appreciation if the parcel is the right one. The fit is specialized: results vary a lot "
        "from house to house, and flood exposure along the Scioto makes this a higher-risk hold than the "
        "rental numbers alone suggest."
    ),
    "central hilltop": (
        "Central Hilltop has strong redevelopment potential, but it is highly parcel-dependent and carries "
        "higher risk than a straightforward residential neighbourhood. Treat it as a mixed opportunity, "
        "not a default search area."
    ),
    "franklinton": (
        "Franklinton, including The Bottoms, has very high appreciation potential and high rental demand "
        "because of redevelopment. Flood exposure is the problem. Climate resilience is scored very low, "
        "and the match score is capped, so a strong appreciation case does not keep a listing near the top. "
        "Judge flood on the specific parcel, and do not treat the neighbourhood colour as a reason to ignore it."
    ),
    "the bottoms": (
        "The Bottoms shares Franklinton's redevelopment story: high rental demand and very high appreciation "
        "potential, with serious flood exposure. Climate resilience is scored very low and the match score "
        "is capped. A parcel here needs a clear flood read before it is worth a visit."
    ),
    "weinland park": (
        "Weinland Park is one of the strongest fits. It sits next to Ohio State, so rental demand is high, "
        "and redevelopment still has room to run. Appreciation potential is high. This is an excellent "
        "area when the property itself is a legal multi-unit in a sensible price range."
    ),
    "italian village": (
        "Italian Village is highly desirable and walkable, with strong rents and strong appreciation. "
        "Supply is constrained, so good listings are scarce. It ranks with the best inner neighbourhoods "
        "for a long-term hold."
    ),
    "victorian village": (
        "Victorian Village is a historic, highly desirable area with constrained supply. Rental demand and "
        "appreciation are both high. The housing stock is attractive, and the limit is finding a property "
        "that still fits the price and unit count."
    ),
    "old north": (
        "Old North has high rental demand from its proximity to Ohio State, including student renters, "
        "and medium-high appreciation potential. It is a strong area, a step below the top inner neighbourhoods "
        "because appreciation is less established."
    ),
    "olde towne east": (
        "Olde Towne East combines high rental demand with high appreciation. It is central, and "
        "redevelopment is still supporting values. A strong long-term hold when the building does not need "
        "a major renovation."
    ),
    "merion village": (
        "Merion Village has high rental demand, a desirable location, and continued neighbourhood momentum. "
        "Appreciation potential is high. It belongs with the stronger inner neighbourhoods."
    ),
    "bexley": (
        "Bexley has high long-term appreciation and a very desirable residential setting. It is more "
        "owner-occupied, so rental and multifamily opportunities are only medium. Buy the location, "
        "and do not expect the easiest rental economics."
    ),
    "upper arlington": (
        "Upper Arlington has excellent appreciation and desirability. Multifamily inventory is limited, "
        "so rental potential is medium. It fits when a legal rental actually exists at a workable price."
    ),
    "new albany": (
        "New Albany has strong growth and high appreciation, with a relatively shallow rental market. "
        "Rental potential is medium. It is a strong suburb for values, and a thinner fit for pure rental yield."
    ),
    "berwick": (
        "Berwick is a mature residential area next to Bexley, with solid housing stock. Appreciation is "
        "medium-high and rental demand is medium. It is less dynamic than the top inner neighbourhoods, "
        "and still a respectable long-term hold."
    ),
    "whitehall": (
        "Whitehall has a strong renter base and an affordable way in, so rental potential is high. "
        "Appreciation is medium, with some upside from East Main transit. A moderate area: the rent "
        "story is better than the appreciation story."
    ),
    "westgate": (
        "Westgate is a stable residential area with medium-high appreciation and medium rental demand. "
        "West Broad transit and redevelopment are the upside. A moderate, selective fit."
    ),
    "near east": (
        "The Near East Side and nearby East Columbus listings benefit from downtown proximity and "
        "redevelopment. Rental demand is high and appreciation is medium. Worth a look when the "
        "property is clean, and not a blanket buy for the whole east side."
    ),
    "east columbus": (
        "East Columbus here means the closer-in east side, with high rental demand and medium appreciation "
        "from downtown proximity and redevelopment. Farther-out east side labels are a weaker fit."
    ),
    "king-lincoln": (
        "King-Lincoln Bronzeville is central, with high rental demand and medium-high appreciation as "
        "redevelopment continues. A moderate-to-strong area, still selective on condition and price."
    ),
    "bronzeville": (
        "Bronzeville shares King-Lincoln's case: a central location, high rental demand, and medium-high "
        "appreciation tied to redevelopment. Judge the building, not just the name."
    ),
    "eastmoor": (
        "Eastmoor is a stable residential area near Bexley. Appreciation potential is medium-high and "
        "rental demand is medium. A moderate fit: pleasant and established, without the momentum of the "
        "top inner neighbourhoods."
    ),
    "clintonville": (
        "Clintonville has high rental demand and high appreciation, and it is expensive. Inventory that "
        "fits a budget around $300k is limited. Desirability is real, and the price is the constraint."
    ),
    "old beechwold": (
        "Beechwold is a desirable residential pocket with high appreciation and only medium rental inventory. "
        "Strong as a place to own, thinner as a multifamily search."
    ),
    "beechwold": (
        "Beechwold has high appreciation and medium rental potential. It is desirable and mostly "
        "owner-occupied, so legal rentals are scarce."
    ),
    "grandview": (
        "Grandview Heights has an excellent location and high appreciation. Prices are high and "
        "multifamily inventory is limited, so rental potential is medium. A moderate fit at this budget."
    ),
    "fifth by northwest": (
        "Fifth by Northwest benefits from Ohio State proximity. Rental demand is high and appreciation "
        "is medium-high, with ongoing redevelopment. A moderate area with a real rental case."
    ),
    "university district": (
        "The University District has very high rental demand, mostly students. Appreciation is medium. "
        "Tenant turnover and management intensity are the drawback, so it stays a selective area rather "
        "than an automatic priority."
    ),
    "dublin": (
        "Dublin has strong jobs, schools, and high appreciation. It is expensive, and multifamily "
        "opportunities are weaker, so rental potential is medium. A moderate fit for this search."
    ),
    "worthington": (
        "Worthington has high appreciation and a desirable setting. Affordable multifamily inventory "
        "is limited, so rental potential is medium. Selective unless the numbers work at the asking price."
    ),
    "hilliard": (
        "Hilliard offers solid suburban growth. Appreciation is medium-high and rental demand is medium. "
        "A reasonable moderate-area hold, not an inner-core priority."
    ),
    "grove city": (
        "Grove City balances affordability, medium-high rental demand, and medium appreciation, with "
        "room for future growth. A moderate suburban fit."
    ),
    "hilltop": (
        "Hilltop is affordable, with medium-high rental demand and medium appreciation. West Broad "
        "transit and redevelopment are the upside. Selective: the area helps, and the building still "
        "has to be straightforward to own."
    ),
    "franklin park": (
        "Franklin Park has a good location and some redevelopment potential. Rental demand and "
        "appreciation are both medium, so the investment profile is mixed rather than excellent."
    ),
    "driving park": (
        "Driving Park is affordable and improving, with high rental demand and medium appreciation. "
        "Neighbourhood quality varies block to block, so this is a mixed opportunity."
    ),
    "southern orchards": (
        "Southern Orchards is central, with high rental demand, medium appreciation, and real "
        "redevelopment potential. Variability and risk are higher than in the green neighbourhoods."
    ),
    "hungarian village": (
        "Hungarian Village is central and improving, with high rental demand and medium appreciation. "
        "The housing and industrial mix keeps it a specialized, higher-variability opportunity."
    ),
    "milo-grogan": (
        "Milo-Grogan is very central, with high rental demand and medium appreciation. Redevelopment "
        "is possible, and the industrial context is a drawback. Mixed, parcel by parcel."
    ),
    "linden": (
        "Linden has strong renter demand and affordable prices, so rental potential is high. "
        "Appreciation is medium. Tenant and rehab risk are higher, which keeps it a mixed area "
        "rather than a priority search."
    ),
    "woodland park": (
        "Woodland Park has medium rental demand and medium appreciation. A moderate fit: established "
        "and reasonable, but without the momentum of the stronger inner neighbourhoods."
    ),
    "eastgate": (
        "Eastgate is affordable and reasonably positioned. Rental demand and appreciation are both "
        "medium, so appreciation upside is limited. A mixed, not a priority, area."
    ),
    "reynoldsburg": (
        "Reynoldsburg has stable suburban rental demand and some East Main transit upside. Rental and "
        "appreciation are both medium. A mixed suburban opportunity."
    ),
    "gahanna": (
        "Gahanna is a strong suburb with medium-high appreciation. At higher prices the rental "
        "economics are less compelling, so rental potential is medium. Mixed for this budget."
    ),
    "westerville": (
        "Westerville has high appreciation as a strong suburb. Multifamily inventory is limited and "
        "prices run higher, so rental potential is medium. A mixed fit for a rental search."
    ),
    "obetz": (
        "Obetz has some industrial and logistics growth, with medium rental demand and low-medium "
        "appreciation. It is a weak fit for a strategy that prefers desirable, resilient neighbourhoods."
    ),
    "groveport": (
        "Groveport is more affordable and farther out. Rental demand is medium and appreciation is "
        "low-medium, with a thinner rental market. A weak fit."
    ),
    "canal winchester": (
        "Canal Winchester is growing, with medium rental demand and low-medium appreciation. It is "
        "a weaker match for this strategy than the closer-in neighbourhoods."
    ),
    "north central": (
        "Shepard and North Central have medium rental demand and low-medium appreciation. Rents and "
        "long-term upside are both on the weak side."
    ),
    "shepard": (
        "Shepard has medium rental demand and low-medium appreciation. Lower rents and weaker "
        "long-term upside make it a poor fit compared with the stronger neighbourhoods."
    ),
    "shepherd": (
        "Shepherd has medium rental demand and low-medium appreciation. It is on the weak end of "
        "the ranking for both rent quality and long-term value."
    ),
}


def neighbourhood_evaluation(label: object) -> tuple[str, str] | None:
    """Return (colour label, evaluation paragraph) for a neighbourhood name."""
    hay = _norm(label)
    if not hay:
        return None
    profile = resolve_neighbourhood_profile(label)
    text = ""
    for tier, needle, _appreciation, _rental in _PROFILES:
        del tier
        if needle in hay and needle in _EVALUATIONS:
            text = _EVALUATIONS[needle]
            break
    if profile is None and not text:
        return None
    colour = tier_short_label(profile.tier) if profile else "Unranked"
    rental = _band_label(profile.rental) if profile else "unknown"
    appreciation = _band_label(profile.appreciation) if profile else "unknown"
    lead = (
        f"Against the rental and appreciation criteria, this area is {colour.lower()}. "
        f"Rental potential is {rental}. Appreciation potential is {appreciation}."
    )
    if text:
        return colour, f"{lead} {text}"
    return colour, lead
