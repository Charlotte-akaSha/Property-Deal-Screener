"""Parse strategy weights and compute weighted overall score."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from utils import load_strategy_raw

CATEGORIES = [
    "financial",
    "location",
    "property",
    "appreciation",
    "rental",
    "management",
    "lifestyle",
    "climate",
    "risk",
]


def parse_weights(strategy_md: str | None = None) -> dict[str, float]:
    text = strategy_md if strategy_md is not None else load_strategy_raw()
    match = re.search(r"```yaml\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError("strategy.md is missing a fenced ```yaml``` weights block at the top.")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict) or "weights" not in data:
        raise ValueError("YAML block must contain a top-level 'weights' mapping.")
    weights = data["weights"]
    if not isinstance(weights, dict):
        raise ValueError("'weights' must be a mapping of category -> float.")

    missing = [c for c in CATEGORIES if c not in weights]
    if missing:
        raise ValueError(f"Missing weight categories: {', '.join(missing)}")

    parsed = {c: float(weights[c]) for c in CATEGORIES}
    total = sum(parsed.values())
    if abs(total - 1.0) > 0.001:
        raise ValueError(f"Weights must sum to 1.0 (got {total:.6f}).")
    return parsed


def compute_overall(categories: dict[str, Any], weights: dict[str, float] | None = None) -> float:
    w = weights if weights is not None else parse_weights()
    overall = 0.0
    for key in CATEGORIES:
        if key not in categories:
            raise ValueError(f"Missing category score: {key}")
        score = float(categories[key])
        if score < 0 or score > 10:
            raise ValueError(f"Category {key} score out of range 0–10: {score}")
        overall += score * w[key]
    return round(overall, 2)


# Your /10 (Wow Factor) blends into displayed match when set: (1-w)*AI + w*you
PERSONAL_MATCH_WEIGHT = 0.20


def wow_factor_value(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # NaN
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0 or score > 10:
        return None
    return round(score, 2)


def blend_with_personal_score(ai_overall: float, personal: float) -> float:
    w = PERSONAL_MATCH_WEIGHT
    return round((1.0 - w) * ai_overall + w * personal, 2)
