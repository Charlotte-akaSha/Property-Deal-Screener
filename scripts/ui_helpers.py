"""Shared Streamlit display helpers."""

from __future__ import annotations

import re

import streamlit as st

from utils import join_list


def render_bullet_list(items: list | None, *, empty_label: str = "_(none)_") -> None:
    text = join_list(items)
    if not text:
        st.markdown(empty_label)
        return
    lines = [line[2:] if line.startswith("• ") else line for line in text.split("\n")]
    st.markdown("\n".join(f"- {line}" for line in lines))


def render_category_scores(categories: dict) -> None:
    lines = [
        f"- **{name.replace('_', ' ').title()}:** {score}/10"
        for name, score in categories.items()
    ]
    st.markdown("\n".join(lines))


def rationale_to_bullets(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if "\n" in text or " | " in text:
        return [
            line[2:] if line.startswith("• ") else line
            for line in join_list([text]).split("\n")
        ]
    parts = re.split(r"(?<=[.!?])\s+", text)
    if len(parts) <= 1:
        return [text]
    return [part.strip() for part in parts if part.strip()]


def format_currency(value: object, *, suffix: str = "") -> str:
    if value is None or value == "":
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    label = f"${amount:,.0f}"
    return f"{label}{suffix}" if suffix else label


def bullets_to_list(text: object) -> list[str]:
    """Split sheet bullet cells (newline bullets) into a list for join_list."""
    if text is None or (isinstance(text, float) and str(text) == "nan"):
        return []
    raw = str(text).strip()
    if not raw:
        return []
    return [line[2:] if line.startswith("• ") else line for line in raw.split("\n") if line.strip()]
