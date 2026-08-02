"""Streamlit portal: paste listing URL/text, upload photos, run analysis."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from analyze_property import analyze_from_memory  # noqa: E402
from utils import MAX_PHOTOS  # noqa: E402
from write_to_sheets import list_regions, sheet_url  # noqa: E402

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

    with st.spinner("Extracting facts and scoring against your strategy…"):
        try:
            result = analyze_from_memory(
                listing_text,
                link=listing_url.strip(),
                property_label=property_label.strip() or None,
                image_uploads=uploads or None,
                sheet_tab=region if not skip_sheets else None,
                skip_sheets=skip_sheets,
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Analysis failed (nothing was written): {exc}")
            st.stop()

    analysis = result["analysis"]
    scored = analysis["scored"]
    extracted = analysis["extracted"]

    st.success(
        f"Saved locally to `{result['folder']}` — "
        f"Overall **{scored['overall']}/10** — {scored['recommendation']}"
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
        st.write(f"**Price:** {extracted.get('price')}")
    with c2:
        st.subheader("Category scores")
        st.json(scored["categories"])

    st.subheader("Strengths")
    for item in scored.get("strengths") or []:
        st.markdown(f"- {item}")
    st.subheader("Weaknesses")
    for item in scored.get("weaknesses") or []:
        st.markdown(f"- {item}")
    st.subheader("Red flags")
    for item in scored.get("red_flags") or []:
        st.markdown(f"- {item}")
    st.subheader("Questions to ask")
    for item in scored.get("questions_to_ask") or []:
        st.markdown(f"- {item}")
    if scored.get("rationale"):
        st.subheader("Rationale")
        st.write(scored["rationale"])
