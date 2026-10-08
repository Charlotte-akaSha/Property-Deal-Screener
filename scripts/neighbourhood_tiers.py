"""Columbus-area search tiers, colours, and area-level appreciation / rental notes."""

from __future__ import annotations

import re
from dataclasses import dataclass

PRIORITY = 1       # Dark green — priority search
STRONG = 2         # Light green — strong
SELECTIVE = 3      # Yellow — selective
OPPORTUNISTIC = 4  # Orange — opportunistic
LOW = 5            # Red — out-of-market / low priority

RULES_VERSION = 10

# (tier, substring, appreciation /10, rental /10) — first match wins
_PROFILES: tuple[tuple[int, str, float, float], ...] = (
    # Outskirts before core names
    (OPPORTUNISTIC, "canal winchester outskirts", 7.5, 7.0),
    (OPPORTUNISTIC, "groveport outskirts", 6.5, 7.5),
    (LOW, "port jervis", 4.0, 5.0),
    (LOW, "croton-on-hudson", 4.0, 5.0),
    (LOW, "ossining", 4.0, 5.0),
    (LOW, "lake peekskill", 4.0, 5.0),
    (LOW, "montrose", 4.0, 5.0),
    (LOW, "cortlandt manor", 4.0, 5.0),
    # Dark green — priority search
    (PRIORITY, "clintonville", 9.0, 8.0),
    (PRIORITY, "old beechwold", 9.0, 8.0),
    (PRIORITY, "beechwold", 9.0, 8.0),
    (PRIORITY, "bexley", 9.0, 8.0),
    (PRIORITY, "berwick", 8.5, 8.5),
    (PRIORITY, "franklinton", 9.0, 9.0),
    (PRIORITY, "olde towne east", 8.5, 9.0),
    (PRIORITY, "near east", 8.5, 9.0),
    (PRIORITY, "merion village", 8.5, 8.5),
    (PRIORITY, "eastmoor", 8.0, 8.5),
    (PRIORITY, "franklin park", 8.5, 8.0),
    (PRIORITY, "grandview heights", 9.0, 7.5),
    (PRIORITY, "grandview", 9.0, 7.5),
    # Light green — strong
    (STRONG, "grove city", 8.0, 8.0),
    (STRONG, "hilliard", 8.0, 7.5),
    (STRONG, "worthington estates", 9.0, 6.5),
    (STRONG, "old worthington", 9.0, 6.5),
    (STRONG, "worthington", 9.0, 6.5),
    (STRONG, "gahanna", 8.0, 7.5),
    (STRONG, "westerville", 8.0, 7.0),
    (STRONG, "upper arlington", 9.0, 6.0),
    (STRONG, "new albany", 9.5, 5.5),
    (STRONG, "westgate", 7.5, 7.0),
    (STRONG, "eastgate", 7.5, 7.0),
    (STRONG, "south hilltop", 7.5, 7.5),
    (STRONG, "hilltop", 7.5, 7.5),
    (STRONG, "dublin", 8.5, 6.5),
    # Yellow — selective
    (SELECTIVE, "king-lincoln", 7.5, 8.0),
    (SELECTIVE, "bronzeville", 7.5, 8.0),
    (SELECTIVE, "driving park", 7.5, 8.0),
    (SELECTIVE, "southern orchards", 7.5, 8.0),
    (SELECTIVE, "hungarian village", 7.5, 7.5),
    (SELECTIVE, "university district", 7.0, 8.5),
    (SELECTIVE, "old north columbus", 7.0, 8.0),
    (SELECTIVE, "fifth by northwest", 7.5, 7.5),
    (SELECTIVE, "north linden", 6.5, 8.0),
    (SELECTIVE, "south linden", 6.5, 8.0),
    (SELECTIVE, "milo-grogan", 6.5, 8.0),
    (SELECTIVE, "linden", 6.5, 8.0),
    (SELECTIVE, "whitehall", 6.5, 8.0),
    (SELECTIVE, "reynoldsburg", 7.0, 7.5),
    (SELECTIVE, "canal winchester", 7.5, 7.0),
    (SELECTIVE, "groveport", 6.5, 7.5),
    (SELECTIVE, "obetz", 6.5, 7.0),
    (SELECTIVE, "valleyview", 6.5, 7.0),
    (SELECTIVE, "lincoln village", 6.0, 7.5),
    (SELECTIVE, "north central", 6.0, 7.0),
    (SELECTIVE, "shepard", 6.0, 7.0),
    (SELECTIVE, "shepherd", 6.0, 7.0),
    # Orange — opportunistic
    (OPPORTUNISTIC, "lancaster", 6.0, 8.0),
    (OPPORTUNISTIC, "kirkersville", 4.5, 9.0),
    (OPPORTUNISTIC, "galloway", 6.0, 7.0),
    (OPPORTUNISTIC, "westland", 5.5, 7.0),
    (OPPORTUNISTIC, "georgesville", 5.5, 7.0),
    (OPPORTUNISTIC, "trabue", 6.0, 6.5),
    (OPPORTUNISTIC, "far west", 5.5, 6.5),
    (OPPORTUNISTIC, "west columbus", 5.5, 6.5),
    (OPPORTUNISTIC, "far east", 5.5, 6.5),
    (OPPORTUNISTIC, "east columbus", 5.5, 6.5),
    (OPPORTUNISTIC, "far south", 5.5, 6.5),
    (OPPORTUNISTIC, "southwest columbus", 5.5, 6.5),
    (OPPORTUNISTIC, "south columbus", 5.5, 6.5),
    (OPPORTUNISTIC, "southeast columbus", 5.5, 6.5),
    (OPPORTUNISTIC, "northeast columbus", 5.5, 6.5),
    (OPPORTUNISTIC, "northland", 5.5, 6.5),
    (OPPORTUNISTIC, "pickerington", 6.0, 7.0),
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
        PRIORITY: "Priority search",
        STRONG: "Strong",
        SELECTIVE: "Selective",
        OPPORTUNISTIC: "Opportunistic",
        LOW: "Low priority",
    }.get(tier or 0, "")
