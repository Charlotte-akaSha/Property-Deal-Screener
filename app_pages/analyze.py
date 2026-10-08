"""Analyze page: paste a listing, upload photos, run the scoring pipeline."""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import theme_css  # noqa: E402
import analyze_property as _analyze_property  # noqa: E402

analyze_from_memory = _analyze_property.analyze_from_memory
from ui_helpers import (  # noqa: E402
    clear_pasted_photos,
    collect_image_uploads,
    pasted_photos,
    format_currency,
    normalize_listing_url,
    rationale_to_bullets,
    render_bullet_list,
    render_category_scores,
    render_clipboard_photo_picker,
)
from composer_llm import probe_composer_api  # noqa: E402
from utils import (  # noqa: E402
    MAX_PHOTOS,
    analysis_backend,
    is_gemini_quota_error,
    is_transient_api_error,
)
from write_to_sheets import list_regions, sheet_url  # noqa: E402

theme_css.hero(
    "Analyze a listing",
    "Paste the listing, add screenshots and your own notes — get scores and a Sheet row.",
    icon="auto_awesome",
)

_backend = analysis_backend()
if _backend == "composer":
    _composer_ok, _composer_msg = probe_composer_api()
    if _composer_ok:
        st.success(_composer_msg, icon=":material/check_circle:")
    else:
        st.error(
            "**Cursor / Composer analysis is configured but the local bridge is not running.**\n\n"
            "Your Cursor subscription is used through a small app on your Mac (not through chat in the IDE).\n\n"
            "1. [Cursor Dashboard → API keys](https://cursor.com/dashboard/api) → **User API keys** → create a key\n"
            "2. Install **[API for Cursor](https://github.com/standardagents/composer-api)** (macOS), paste the key, **Start server** (port **8787**)\n"
            "3. In `.env`: `ANALYSIS_BACKEND=composer`, `COMPOSER_API_BASE_URL=http://127.0.0.1:8787/v1`, "
            "`COMPOSER_API_KEY=local`, `COMPOSER_MODEL=composer-2.5-fast`\n"
            "4. Terminal check: `python3 scripts/check_composer.py` — then rerun Streamlit\n\n"
            f"Details: `docs/composer-setup.md` — diagnostic: {_composer_msg}",
            icon=":material/link_off:",
        )
else:
    st.caption(f"Analysis backend: **Gemini** (`GEMINI_API_KEY`). For Cursor billing instead, see `docs/composer-setup.md`.")

form_col, tips_col = st.columns([2, 1], gap="large")

with form_col:
    with theme_css.card("input"):
        theme_css.section("Listing input", "content_paste", "violet")
        listing_url = st.text_input(
            "Listing URL (optional)",
            placeholder="https://www.zillow.com/...",
            key="analyze_listing_url",
        )
        listing_text = st.text_area(
            "Listing text (required)",
            height=210,
            placeholder="Paste the description and facts you copied from the listing site…",
            key="analyze_listing_text",
        )
        user_comments = st.text_area(
            "Your comments (optional)",
            height=110,
            placeholder="Your notes, concerns, or observations about this property…",
            help="Included in extraction and scoring alongside the listing text.",
            key="analyze_user_comments",
        )
        render_clipboard_photo_picker()
        photos = st.file_uploader(
            f"Or upload photos / screenshots (max {MAX_PHOTOS} total with pasted images)",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            accept_multiple_files=True,
            key="analyze_photos_upload",
        )
        property_label = st.text_input(
            "Property label override (optional)",
            help="If set, used as Property ID instead of the address-derived slug.",
            key="analyze_property_label",
        )
        regions = list_regions()
        with st.expander("Advanced"):
            region_override = st.selectbox(
                "Sheet tab override (optional)",
                options=["Auto-detect from address"] + regions,
                help=(
                    "After extraction, the app picks the tab from city/state in the listing. "
                    "Use this only when detection is wrong or the address is incomplete."
                ),
                key="analyze_region_override",
            )
        sheet_tab_override = (
            None
            if region_override == "Auto-detect from address"
            else region_override
        )
        save_to_google_sheets = st.checkbox(
            "Save to Google Sheets",
            value=True,
            help="When unchecked, results are archived locally only.",
            key="analyze_save_sheets",
        )
        submitted = st.button(
            "Analyze property", type="primary", icon=":material/bolt:"
        )

with tips_col:
    with theme_css.card("how"):
        theme_css.section("How it works", "help_outline", "mint")
        st.markdown(
            "1. **Extract** — facts pulled from your text and screenshots\n"
            "2. **Transit** — Google Maps walk + train times to the city hub\n"
            "3. **Score** — categories + neighbourhood research (fast mode, one step)\n"
            "4. **Save** — archived locally and upserted into your Sheet"
        )
    with theme_css.card("tips"):
        theme_css.section("Get better results", "tips_and_updates", "amber")
        st.markdown(
            "- Include the full address (city + state) for transit and the correct Sheet tab\n"
            "- Paste facts tables, not just marketing copy\n"
            "- Paste or upload Zillow screenshots when the text is thin\n"
            "- Use comments for anything the listing hides"
        )

if submitted:
    if _backend == "composer" and not probe_composer_api()[0]:
        st.error(
            "Start the local Composer API bridge on port 8787 before analyzing. "
            "See the red banner above or `docs/composer-setup.md`.",
            icon=":material/error:",
        )
        st.stop()
    if not listing_text.strip():
        st.error("Listing text is required.", icon=":material/error:")
        st.stop()
    pasted = pasted_photos()
    uploads = collect_image_uploads(photos, pasted)
    if len(uploads) > MAX_PHOTOS:
        st.error(f"Please use at most {MAX_PHOTOS} photos in total.", icon=":material/error:")
        st.stop()

    importlib.reload(_analyze_property)
    run_analyze = _analyze_property.analyze_from_memory
    supports_progress = "progress" in inspect.signature(run_analyze).parameters

    with st.status("Starting analysis…", expanded=True) as analysis_status:
        try:
            analyze_kwargs: dict = {
                "link": listing_url.strip(),
                "user_comments": user_comments.strip(),
                "property_label": property_label.strip() or None,
                "image_uploads": uploads or None,
                "sheet_tab": sheet_tab_override,
                "skip_sheets": not save_to_google_sheets,
            }
            if supports_progress:
                analyze_kwargs["progress"] = lambda msg: analysis_status.update(
                    label=msg
                )
            result = run_analyze(listing_text, **analyze_kwargs)
        except Exception as exc:  # noqa: BLE001
            analysis_status.update(label="Analysis failed", state="error")
            if is_gemini_quota_error(exc):
                st.error(
                    "Gemini API quota limit reached for this project/model (often the free tier’s "
                    "daily cap). Enable billing on the same Google Cloud project as your API key, "
                    "wait for the daily reset, or pin a single model in `.env` — e.g. "
                    "`GEMINI_MODEL=gemini-3.6-flash` and avoid fallbacks to models you’ve maxed out "
                    "(remove `gemini-3.8-flash` from `GEMINI_MODEL_FALLBACKS` if set).",
                    icon=":material/speed:",
                )
            elif is_transient_api_error(exc):
                st.error(
                    "Gemini is temporarily overloaded. The app retried automatically but still failed. "
                    "Wait a minute and try again, or set `GEMINI_MODEL` / `GEMINI_MODEL_FALLBACKS` in `.env` "
                    "(e.g. `GEMINI_MODEL=gemini-3.6-flash`).",
                    icon=":material/cloud_off:",
                )
            else:
                st.error(f"Analysis failed (nothing was written): {exc}", icon=":material/error:")
            st.stop()
        analysis_status.update(label="Analysis complete", state="complete", expanded=False)

    clear_pasted_photos()

    analysis = result["analysis"]
    scored = analysis["scored"]
    extracted = analysis["extracted"]
    transit = analysis.get("transit") or {}
    sheet_tab_used = analysis.get("meta", {}).get("sheet_tab") or scored.get("region")

    st.space("medium")
    theme_css.section("Results", "verified", "mint")

    listing_link = normalize_listing_url(
        st.session_state.get("analyze_listing_url") or extracted.get("link")
    )
    address = str(extracted.get("address") or "").strip()
    price_card: tuple = (
        "Price",
        format_currency(extracted.get("price")),
        "sell",
        "peach",
        address,
    )
    if listing_link and address:
        price_card = (*price_card, listing_link)

    theme_css.kpi_grid(
        [
            ("Match score", f"{scored['overall']}/10", "speed", "violet",
             scored["recommendation"]),
            price_card,
            (
                "Gross income / yr",
                format_currency(extracted.get("gross_annual_income"))
                if extracted.get("gross_annual_income")
                else format_currency(
                    (extracted.get("estimated_rent") or 0) * 12
                    if extracted.get("estimated_rent")
                    else None
                ),
                "savings",
                "mint",
                "from listing"
                if extracted.get("gross_annual_income")
                else "AI estimate",
            ),
            ("Est. rent / mo", format_currency(extracted.get("estimated_rent")),
             "payments", "blue", "monthly"),
            ("Annual tax", format_currency(extracted.get("taxes")),
             "receipt_long", "amber", "from listing"),
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
                is_columbus = transit.get("transit_mode") == "cota_bus"
                walk_label = "Walk to bus stop" if is_columbus else "Walk to station"
                commute_label = (
                    "Transit to Downtown Columbus"
                    if is_columbus
                    else "Train to city center"
                )
                lines = [
                    f"- **{walk_label}:** {transit.get('walk_to_station', '')} "
                    f"({transit.get('nearest_station', '')})",
                    f"- **{commute_label}:** {transit.get('train_to_city_center', '')} "
                    f"(dep. {transit.get('train_departure_at', 'Mon 8:00 AM')}) "
                    f"→ {transit.get('city_center', '')}",
                ]
                if transit.get("transit_to_osu"):
                    lines.append(
                        f"- **Transit to OSU:** {transit.get('transit_to_osu', '')} "
                        f"({transit.get('transfers_to_osu', 0)} transfer(s))"
                    )
                if not is_columbus:
                    lines.append(
                        f"- **Total door to door:** {transit.get('total_to_city_center', '')}"
                    )
                else:
                    lines.append(
                        f"- **Door to door (Downtown):** {transit.get('total_to_city_center', '')}"
                    )
                    if transit.get("transfers_to_downtown") is not None:
                        lines.append(
                            f"- **Transfers to Downtown:** {transit.get('transfers_to_downtown', 0)}"
                        )
                st.markdown("\n".join(lines))

        regional = scored.get("regional_assessment")
        if regional:
            with theme_css.card("columbus"):
                theme_css.section(
                    "Columbus accessibility", "location_city", "mint"
                )
                st.markdown(
                    "\n".join(
                        [
                            f"- **Current transit:** {regional.get('current_transit')}/10 "
                            f"(Tier {regional.get('transit_tier', '?')})",
                            f"- **Future transit investment:** "
                            f"{regional.get('future_transit_investment')}/10",
                            f"- **Transit appreciation potential:** "
                            f"{regional.get('transit_appreciation_potential')}/10",
                            f"- **Green / low-density:** "
                            f"{regional.get('green_low_density_quality')}/10",
                            f"- **Flood risk (10=low):** {regional.get('flood_risk')}/10",
                            f"- **Climate resilience:** "
                            f"{regional.get('overall_climate_resilience')}/10",
                            f"- **Car independence:** {regional.get('car_independence')}/10",
                            f"- **Overall accessibility:** "
                            f"{regional.get('overall_accessibility_score')}/10",
                            f"- **Multi-unit / income:** "
                            f"{regional.get('multi_unit_score')}/10 "
                            f"(Tier {regional.get('multi_unit_property_tier', '?')})",
                            f"- **Owner-occupancy fit:** "
                            f"{regional.get('owner_occupancy_fit')}/10",
                            f"- **Trailer storage:** "
                            f"{regional.get('trailer_storage_score')}/10",
                            f"- **Combined investment fit:** "
                            f"{regional.get('combined_investment_fit')}/10",
                            f"- **Future catalyst:** "
                            f"{regional.get('future_transit_catalyst', '')}",
                        ]
                    )
                )
                if regional.get("final_strategy_answer"):
                    st.markdown(regional["final_strategy_answer"])
                if regional.get("future_transit_detail"):
                    st.markdown("**Transit plans (research)**")
                    st.markdown(regional["future_transit_detail"])
                elif regional.get("future_transit_catalyst_note"):
                    st.caption(regional["future_transit_catalyst_note"])
                st.markdown("**Why attractive**")
                render_bullet_list(regional.get("why_attractive"))
                st.markdown("**Main risks**")
                render_bullet_list(regional.get("main_risks"))

    with right:
        with theme_css.card("saved"):
            theme_css.section("Saved", "cloud_done", "mint")
            st.caption(f"Local archive: `{result['folder']}`")
            if not save_to_google_sheets:
                st.info(
                    "Saved locally only — Google Sheets was not updated.",
                    icon=":material/folder:",
                )
            elif result.get("sheets_error"):
                st.error(
                    "Analysis succeeded, but the Sheet update failed. Local files were saved.\n\n"
                    f"`{result['sheets_error']}`",
                    icon=":material/warning:",
                )
                st.caption(f"Retry with: `python scripts/write_to_sheets.py {result['folder']}`")
            elif result.get("sheets"):
                tab = result["sheets"].get("sheet_tab") or sheet_tab_used or ""
                st.session_state["sheets_cache_generation"] = (
                    st.session_state.get("sheets_cache_generation", 0) + 1
                )
                if tab:
                    st.session_state["compare_active_region"] = tab
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
    theme_css.render_market_research_sections(scored)

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
