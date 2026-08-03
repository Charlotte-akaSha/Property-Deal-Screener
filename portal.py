"""Streamlit portal: paste listing URL/text, upload photos, run analysis."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from analyze_property import analyze_from_memory  # noqa: E402
from utils import MAX_PHOTOS, is_transient_api_error, join_list  # noqa: E402
from write_to_sheets import list_regions, sheet_url  # noqa: E402


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
        return [line[2:] if line.startswith("• ") else line for line in join_list([text]).split("\n")]
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


regions = list_regions()

st.set_page_config(page_title="AI Real Estate Assistant", layout="centered")
st.title("AI Real Estate Acquisition Assistant")
st.caption("Paste a listing, upload up to 5 screenshots, get scores + a Google Sheets row.")

with st.form("analyze_form"):
    listing_url = st.text_input("Listing URL (optional)", placeholder="https://www.zillow.com/...")
    listing_text = st.text_area(
        "Listing text (required)",
        height=220,
        placeholder="Paste the description and facts you copied from the listing site…",
    )
    user_comments = st.text_area(
        "User comments (optional)",
        height=120,
        placeholder="Your notes, concerns, or observations about this property…",
        help="Included in extraction and scoring alongside the listing text.",
    )
    photos = st.file_uploader(
        f"Photos / screenshots (optional, max {MAX_PHOTOS})",
        type=["png", "jpg", "jpeg", "webp", "gif"],
        accept_multiple_files=True,
    )
    property_label = st.text_input(
        "Property label override (optional)",
        help="If set, used as Property ID instead of the address-derived slug.",
    )
    region = st.selectbox(
        "Region (Google Sheet tab)",
        options=regions,
        help="Each region is a separate tab in your spreadsheet with the same columns.",
    )
    skip_sheets = st.checkbox("Skip Google Sheets write", value=False)
    submitted = st.form_submit_button("Analyze", type="primary")

if submitted:
    if not listing_text.strip():
        st.error("Listing text is required.")
        st.stop()
    if photos and len(photos) > MAX_PHOTOS:
        st.error(f"Please upload at most {MAX_PHOTOS} photos.")
        st.stop()

    uploads: list[tuple[str, bytes]] = []
    if photos:
        for f in photos[:MAX_PHOTOS]:
            uploads.append((f.name, f.getvalue()))

    with st.spinner("Extracting facts, looking up transit, and scoring…"):
        try:
            result = analyze_from_memory(
                listing_text,
                link=listing_url.strip(),
                user_comments=user_comments.strip(),
                property_label=property_label.strip() or None,
                image_uploads=uploads or None,
                sheet_tab=region,
                skip_sheets=skip_sheets,
            )
        except Exception as exc:  # noqa: BLE001
            if is_transient_api_error(exc):
                st.error(
                    "Gemini is temporarily overloaded. The app retried automatically but still failed. "
                    "Wait a minute and try again, or set `GEMINI_MODEL=gemini-2.5-flash` in `.env` as a fallback."
                )
            else:
                st.error(f"Analysis failed (nothing was written): {exc}")
            st.stop()

    analysis = result["analysis"]
    scored = analysis["scored"]
    extracted = analysis["extracted"]
    transit = analysis.get("transit") or {}

    st.success(
        f"Saved locally to `{result['folder']}` — "
        f"Overall **{scored['overall']}/10** — {scored['recommendation']}"
    )

    if transit:
        st.subheader("Transit (Google Maps)")
        st.markdown(
            "\n".join(
                [
                    f"- **Walk to station:** {transit.get('walk_to_station', '')} "
                    f"({transit.get('nearest_station', '')})",
                    f"- **Train to city center:** {transit.get('train_to_city_center', '')} "
                    f"(dep. {transit.get('train_departure_at', 'Mon 8:00 AM')}) "
                    f"→ {transit.get('city_center', '')}",
                    f"- **Total to city center:** {transit.get('total_to_city_center', '')} "
                    "(walk + train)",
                ]
            )
        )

    if result.get("sheets_error"):
        st.error(
            "Analysis succeeded, but Sheet update failed. "
            f"Local files were saved. Error: {result['sheets_error']}\n\n"
            f"Retry with: `python scripts/write_to_sheets.py {result['folder']}`"
        )
    elif result.get("sheets"):
        tab = result["sheets"].get("sheet_tab", region)
        st.info(f"Google Sheets {result['sheets']['action']} OK on tab **{tab}**.")
        st.link_button("Open in Google Sheets", result["sheets"]["sheet_url"])
    elif not skip_sheets:
        st.link_button("Open in Google Sheets", sheet_url())

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Overall")
        st.metric("Match", f"{scored['overall']}/10")
        st.write(f"**Recommendation:** {scored['recommendation']}")
        st.write(f"**Address:** {extracted.get('address', '')}")
        st.write(f"**Price:** {format_currency(extracted.get('price'))}")
        st.markdown(
            "\n".join(
                [
                    f"- **Est. rent (mo):** {format_currency(extracted.get('estimated_rent'))}",
                    f"- **Est. insurance (yr):** {format_currency(extracted.get('estimated_insurance'))}",
                ]
            )
        )
    with c2:
        st.subheader("Category scores")
        render_category_scores(scored["categories"])

    st.subheader("Strengths")
    render_bullet_list(scored.get("strengths"))
    st.subheader("Weaknesses")
    render_bullet_list(scored.get("weaknesses"))
    st.subheader("Red flags")
    render_bullet_list(scored.get("red_flags"))
    st.subheader("Questions to ask")
    render_bullet_list(scored.get("questions_to_ask"))
    if scored.get("rationale"):
        st.subheader("Rationale")
        render_bullet_list(rationale_to_bullets(scored["rationale"]))
