"""Shared Streamlit display helpers."""

from __future__ import annotations

import hashlib
import html
import io
import re
from typing import Any

import streamlit as st
from PIL import Image
from streamlit_paste_button import paste_image_button
from streamlit_sortables import sort_items

from utils import MAX_PHOTOS, join_list

PASTED_PHOTOS_KEY = "pasted_photos"
PASTED_HASHES_KEY = "pasted_photo_hashes"
PASTE_GENERATION_KEY = "paste_button_generation"


def normalize_listing_url(url: object) -> str:
    raw = str(url or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return ""


def property_title_html(name: str, link: object) -> str:
    """Property name for compare table — links to listing when URL is known."""
    safe_name = html.escape(name)
    url = normalize_listing_url(link)
    if url:
        return (
            f'<a class="pc-prop-name pc-prop-link" href="{html.escape(url)}" '
            f'target="_blank" rel="noopener noreferrer">{safe_name}</a>'
        )
    return f'<div class="pc-prop-name">{safe_name}</div>'


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


def pasted_photos() -> list[tuple[str, bytes]]:
    if PASTED_PHOTOS_KEY not in st.session_state:
        st.session_state[PASTED_PHOTOS_KEY] = []
    return st.session_state[PASTED_PHOTOS_KEY]


def _ensure_pasted_photos_state() -> list[tuple[str, bytes]]:
    return pasted_photos()


def clear_pasted_photos() -> None:
    st.session_state[PASTED_PHOTOS_KEY] = []
    st.session_state[PASTED_HASHES_KEY] = set()
    st.session_state[PASTE_GENERATION_KEY] = 0


def _pasted_hashes() -> set[str]:
    if PASTED_HASHES_KEY not in st.session_state:
        st.session_state[PASTED_HASHES_KEY] = set()
    return st.session_state[PASTED_HASHES_KEY]


def _render_pasted_gallery(pasted: list[tuple[str, bytes]]) -> None:
    """Drag-and-drop reorder + thumbnails for pasted images."""
    if not pasted:
        return
    st.caption(f"{len(pasted)} pasted image(s) — drag chips to reorder")
    sort_keys = [f"#{idx + 1}" for idx in range(len(pasted))]
    sorted_keys = sort_items(
        sort_keys,
        header=None,
        direction="horizontal",
        key="pasted_photos_sort",
        custom_style="""
        .sortable-item {
          font-weight: 600;
          padding: 6px 12px;
          border-radius: 8px;
          background: #eef0f6;
          cursor: grab;
        }
        """,
    )
    if sorted_keys != sort_keys:
        order = [int(k.lstrip("#")) - 1 for k in sorted_keys]
        st.session_state[PASTED_PHOTOS_KEY] = [pasted[i] for i in order]
        st.rerun()
    cols = st.columns(min(len(pasted), MAX_PHOTOS))
    for idx, (name, data) in enumerate(pasted[:MAX_PHOTOS]):
        with cols[idx % len(cols)]:
            st.image(data, caption=f"{idx + 1}. {name}", width="stretch")
    if st.button("Clear pasted images", key="clear_pasted_photos"):
        clear_pasted_photos()
        st.rerun()


def render_clipboard_photo_picker() -> None:
    """Paste images from the system clipboard (e.g. Zillow screenshot)."""
    pasted = _ensure_pasted_photos_state()
    remaining = MAX_PHOTOS - len(pasted)
    st.caption(
        f"Optional: copy **one** image, click **Paste**, repeat until you have up to {MAX_PHOTOS} "
        f"({remaining} slot(s) left with pasted + upload). "
        "If paste is blocked, use **upload** below."
    )
    if remaining <= 0:
        st.caption("Photo limit reached — clear pasted images or remove uploads to paste more.")
    else:
        paste_generation = int(st.session_state.get(PASTE_GENERATION_KEY, 0))
        try:
            paste = paste_image_button(
                f"Paste image from clipboard ({len(pasted)}/{MAX_PHOTOS})",
                background_color="#5b6ee1",
                hover_background_color="#4a5bc4",
                key=f"listing_paste_image_{paste_generation}",
                errors="ignore",
            )
        except Exception:  # noqa: BLE001 — browser may block clipboard read
            paste = None
            st.session_state["clipboard_paste_blocked"] = True
        if st.session_state.get("clipboard_paste_blocked"):
            st.info(
                "Your browser blocked clipboard access (common in Safari or locked-down tabs). "
                "Save the image or take a screenshot, then add it with **upload** below.",
                icon=":material/info:",
            )
        if paste is not None and paste.image_data is not None:
            st.session_state.pop("clipboard_paste_blocked", None)
            buf = io.BytesIO()
            paste.image_data.save(buf, format="PNG")
            data = buf.getvalue()
            digest = hashlib.sha256(data).hexdigest()
            hashes = _pasted_hashes()
            if digest in hashes:
                st.warning("That image is already in your pasted list.")
                st.session_state[PASTE_GENERATION_KEY] = paste_generation + 1
                st.rerun()
            elif len(pasted) >= MAX_PHOTOS:
                st.warning(f"Maximum {MAX_PHOTOS} photos — remove some before pasting more.")
            else:
                pasted.append((f"clipboard_{len(pasted) + 1}.png", data))
                hashes.add(digest)
                st.session_state[PASTE_GENERATION_KEY] = paste_generation + 1
                st.rerun()
    _render_pasted_gallery(pasted)


def collect_image_uploads(
    file_uploads: Any,
    pasted: list[tuple[str, bytes]] | None = None,
) -> list[tuple[str, bytes]]:
    uploads: list[tuple[str, bytes]] = []
    if pasted:
        uploads.extend(pasted[:MAX_PHOTOS])
    if file_uploads:
        for f in file_uploads:
            if len(uploads) >= MAX_PHOTOS:
                break
            uploads.append((f.name, f.getvalue()))
    return uploads[:MAX_PHOTOS]


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
