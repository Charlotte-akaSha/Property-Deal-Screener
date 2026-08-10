"""Analyze page: paste a listing, upload photos, run the scoring pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import theme_css  # noqa: E402
from analyze_property import analyze_from_memory  # noqa: E402
from ui_helpers import (  # noqa: E402
    format_currency,
    rationale_to_bullets,
    render_bullet_list,
    render_category_scores,
)
from utils import MAX_PHOTOS, is_transient_api_error  # noqa: E402
from write_to_sheets import list_regions, sheet_url  # noqa: E402

theme_css.hero(
    "Analyze a listing",
    "Paste the listing, add screenshots and your own notes — get scores and a Sheet row.",
    icon="auto_awesome",
)

regions = list_regions()

form_col, tips_col = st.columns([2, 1], gap="large")

with form_col:
    with theme_css.card("input"):
        theme_css.section("Listing input", "content_paste", "violet")
        with st.form("analyze_form"):
            listing_url = st.text_input(
                "Listing URL (optional)", placeholder="https://www.zillow.com/..."
            )
            listing_text = st.text_area(
                "Listing text (required)",
                height=210,
                placeholder="Paste the description and facts you copied from the listing site…",
            )
            user_comments = st.text_area(
                "Your comments (optional)",
                height=110,
                placeholder="Your notes, concerns, or observations about this property…",
                help="Included in extraction and scoring alongside the listing text.",
            )
            photos = st.file_uploader(
                f"Photos / screenshots (optional, max {MAX_PHOTOS})",
                type=["png", "jpg", "jpeg", "webp", "gif"],
                accept_multiple_files=True,
            )
            opt1, opt2 = st.columns(2)
            with opt1:
                property_label = st.text_input(
                    "Property label override (optional)",
                    help="If set, used as Property ID instead of the address-derived slug.",
                )
            with opt2:
                region = st.selectbox(
                    "Region (Sheet tab)",
                    options=regions,
                    help="Each region is a separate tab with the same columns.",
                )
            submitted = st.form_submit_button(
                "Analyze property", type="primary", icon=":material/bolt:"
            )

with tips_col:
    with theme_css.card("how"):
        theme_css.section("How it works", "help_outline", "mint")
        st.markdown(
            "1. **Extract** — facts pulled from your text and screenshots\n"
            "2. **Transit** — Google Maps walk + train times to the city hub\n"
            "3. **Score** — nine categories weighted by your strategy\n"
            "4. **Save** — archived locally and upserted into your Sheet"
        )
    with theme_css.card("tips"):
        theme_css.section("Get better results", "tips_and_updates", "amber")
        st.markdown(
            "- Include the full address so transit lookup works\n"
            "- Paste facts tables, not just marketing copy\n"
            "- Screenshots fill gaps when the text is thin\n"
            "- Use comments for anything the listing hides"
        )

if submitted:
    if not listing_text.strip():
        st.error("Listing text is required.", icon=":material/error:")
        st.stop()
    if photos and len(photos) > MAX_PHOTOS:
        st.error(f"Please upload at most {MAX_PHOTOS} photos.", icon=":material/error:")
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
            )
        except Exception as exc:  # noqa: BLE001
            if is_transient_api_error(exc):
                st.error(
                    "Gemini is temporarily overloaded. The app retried automatically but still failed. "
                    "Wait a minute and try again, or switch `GEMINI_MODEL` in `.env`.",
                    icon=":material/cloud_off:",
                )
            else:
                st.error(f"Analysis failed (nothing was written): {exc}", icon=":material/error:")
            st.stop()

    analysis = result["analysis"]
    scored = analysis["scored"]
    extracted = analysis["extracted"]
    transit = analysis.get("transit") or {}

    st.space("medium")
    theme_css.section("Results", "verified", "mint")

    theme_css.kpi_grid(
        [
            ("Match score", f"{scored['overall']}/10", "speed", "violet",
             scored["recommendation"]),
            ("Price", format_currency(extracted.get("price")), "sell", "peach",
             extracted.get("address", "")),
            ("Est. rent / mo", format_currency(extracted.get("estimated_rent")),
             "savings", "mint", "AI estimate"),
            ("Est. insurance / yr", format_currency(extracted.get("estimated_insurance")),
             "shield", "blue", "AI estimate"),
        ]
    )

    st.space("small")
    left, right = st.columns(2, gap="medium")

    with left:
        with theme_css.card("cats"):
            theme_css.section("Category scores", "insights", "violet")
            render_category_scores(scored["categories"])
        if transit:
            with theme_css.card("transit"):
                theme_css.section("Transit (Google Maps)", "directions_transit", "blue")
                st.markdown(
                    f"- **Walk to station:** {transit.get('walk_to_station', '')} "
                    f"({transit.get('nearest_station', '')})\n"
                    f"- **Train to city center:** {transit.get('train_to_city_center', '')} "
                    f"(dep. {transit.get('train_departure_at', 'Mon 8:00 AM')}) "
                    f"→ {transit.get('city_center', '')}\n"
                    f"- **Total door to door:** {transit.get('total_to_city_center', '')}"
                )

    with right:
        with theme_css.card("saved"):
            theme_css.section("Saved", "cloud_done", "mint")
            st.caption(f"Local archive: `{result['folder']}`")
            if result.get("sheets_error"):
                st.error(
                    "Analysis succeeded, but the Sheet update failed. Local files were saved.\n\n"
                    f"`{result['sheets_error']}`",
                    icon=":material/warning:",
                )
                st.caption(f"Retry with: `python scripts/write_to_sheets.py {result['folder']}`")
            elif result.get("sheets"):
                tab = result["sheets"].get("sheet_tab", region)
                st.success(
                    f"Google Sheets {result['sheets']['action']} on tab **{tab}**.",
                    icon=":material/check_circle:",
                )
                st.link_button(
                    "Open in Google Sheets", result["sheets"]["sheet_url"],
                    icon=":material/open_in_new:", width="stretch",
                )
            else:
                st.link_button(
                    "Open in Google Sheets", sheet_url(),
                    icon=":material/open_in_new:", width="stretch",
                )
        if scored.get("rationale"):
            with theme_css.card("why"):
                theme_css.section("Why this score", "psychology", "amber")
                render_bullet_list(rationale_to_bullets(scored["rationale"]))

    st.space("small")
    g1, g2 = st.columns(2, gap="medium")
    with g1:
        with theme_css.card("strengths"):
            theme_css.section("Strengths", "thumb_up", "mint")
            render_bullet_list(scored.get("strengths"))
        with theme_css.card("redflags"):
            theme_css.section("Red flags", "report", "rose")
            render_bullet_list(scored.get("red_flags"))
    with g2:
        with theme_css.card("weaknesses"):
            theme_css.section("Weaknesses", "thumb_down", "amber")
            render_bullet_list(scored.get("weaknesses"))
        with theme_css.card("questions"):
            theme_css.section("Questions to ask", "help", "blue")
            render_bullet_list(scored.get("questions_to_ask"))
