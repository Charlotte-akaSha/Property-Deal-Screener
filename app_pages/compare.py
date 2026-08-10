"""Compare page: portfolio dashboard from Google Sheets."""

from __future__ import annotations

import html
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import theme_css  # noqa: E402
from geocode import coordinates_for  # noqa: E402
from photos import (  # noqa: E402
    ensure_thumbnail,
    find_property_photo,
    readable_property_name,
)
from sheets_data import (  # noqa: E402
    PERSONAL_COLUMN_LIST,
    SCORE_COLUMNS,
    load_properties,
    save_personal_edits,
)
from ui_helpers import bullets_to_list, format_currency, render_bullet_list  # noqa: E402
from write_to_sheets import list_regions, sheet_url  # noqa: E402

RECOMMENDATIONS = ["Reject", "Save", "Worth visiting"]
FINAL_DECISIONS = ["Pursue", "Maybe", "Pass", "Visited", "Offer made"]
CHART_HEIGHT = 300

REC_COLORS = {
    "Worth visiting": [61, 155, 143],
    "Save": [109, 94, 245],
    "Reject": [212, 113, 122],
}
DEFAULT_REC_COLOR = [139, 146, 168]

COMPARE_COLUMNS = [
    "Photo",
    "Property",
    "Location",
    "Price",
    "Gross yield %",
    "Overall",
    "Recommendation",
    "Commute (min)",
]

NOTES_COLUMNS = ["Property ID", "Region", "_sheet_row", *PERSONAL_COLUMN_LIST]


@st.cache_data(ttl="10m", show_spinner="Loading properties from Google Sheets…")
def cached_load_properties(regions: tuple[str, ...]) -> pd.DataFrame:
    return load_properties(list(regions))


@st.cache_data(ttl="24h", show_spinner="Locating properties…")
def cached_coordinates(property_ids: tuple[str, ...]) -> dict[str, tuple[float, float]]:
    return coordinates_for(list(property_ids))


def num(value: object, fmt: str = "{:,.0f}", fallback: str = "—") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    try:
        return fmt.format(float(value))
    except (TypeError, ValueError):
        return fallback


def apply_filters(
    df: pd.DataFrame,
    *,
    regions: list[str],
    recommendations: list[str],
    price_range: tuple[float, float],
    min_overall: float,
    max_commute: float | None,
    min_beds: int,
) -> pd.DataFrame:
    out = df.copy()
    if regions:
        out = out[out["Region"].isin(regions)]
    if recommendations:
        out = out[out["Recommendation"].isin(recommendations)]
    if "Price" in out.columns:
        in_range = out["Price"].between(price_range[0], price_range[1], inclusive="both")
        out = out[in_range | out["Price"].isna()]
    out = out[out["Overall"].fillna(0) >= min_overall]
    if max_commute is not None and "Commute (min)" in out.columns:
        out = out[out["Commute (min)"].fillna(9999) <= max_commute]
    if min_beds > 0 and "Bedrooms" in out.columns:
        out = out[out["Bedrooms"].fillna(0) >= min_beds]
    return out


def _to_chip_list(val: object) -> list[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    return [str(val)]


def render_kpis(df: pd.DataFrame) -> None:
    count = len(df)
    best_row = df.loc[df["Overall"].idxmax()] if count and df["Overall"].notna().any() else None

    cards = [
        ("Properties", f"{count:,}", "home_work", "violet", "in current view"),
        ("Avg match", num(df["Overall"].mean(), "{:.1f}") + "/10" if count else "—",
         "speed", "blue", "weighted match"),
        ("Best match",
         (f"{best_row['Overall']:.1f}/10" if best_row is not None else "—"),
         "military_tech", "mint",
         (readable_property_name(best_row["Property ID"]) if best_row is not None else "")),
        ("Median asking price", "$" + num(df["Price"].median()) if count else "—",
         "payments", "peach", "asking price"),
        ("Median gross yield", num(df["Gross yield %"].median(), "{:.1f}") + "%" if count else "—",
         "trending_up", "rose", "gross annual"),
        ("Worth visiting", f"{int((df['Recommendation'] == 'Worth visiting').sum()):,}" if count else "0",
         "flag", "amber", "shortlist"),
    ]

    theme_css.kpi_grid(cards)


def render_property_dialog(row: pd.Series) -> None:
    photo_path = find_property_photo(str(row["Property ID"]))
    if photo_path is not None:
        left, right = st.columns([1.1, 1.4], gap="large")
        with left:
            st.image(str(photo_path), width="stretch")
        with right:
            theme_css.chips(
                [
                    f"{row.get('City', '')}, {row.get('State', '')}",
                    str(row.get("Recommendation", "")),
                    f"Overall {num(row.get('Overall'), '{:.1f}')}/10",
                    f"{row.get('Region', '')}",
                ]
            )
            theme_css.kpi_grid(
                [
                    ("Price", "$" + num(row.get("Price")), "sell", "peach", ""),
                    ("Rent / mo", "$" + num(row.get("Estimated Rent")), "savings", "mint", ""),
                    ("Gross yield", num(row.get("Gross yield %"), "{:.1f}") + "%", "percent", "violet", ""),
                    ("Commute", num(row.get("Commute (min)")) + " min", "train", "blue", ""),
                ],
                min_width="150px",
            )
    else:
        theme_css.chips(
            [
                f"{row.get('City', '')}, {row.get('State', '')}",
                str(row.get("Recommendation", "")),
                f"Overall {num(row.get('Overall'), '{:.1f}')}/10",
                f"{row.get('Region', '')}",
            ]
        )
        theme_css.kpi_grid(
            [
                ("Price", "$" + num(row.get("Price")), "sell", "peach", ""),
                ("Rent / mo", "$" + num(row.get("Estimated Rent")), "savings", "mint", ""),
                ("Gross yield", num(row.get("Gross yield %"), "{:.1f}") + "%", "percent", "violet", ""),
                ("Commute", num(row.get("Commute (min)")) + " min", "train", "blue", ""),
            ],
            min_width="170px",
        )

    st.space("small")
    c1, c2 = st.columns(2)
    with c1:
        with theme_css.card("d_cats"):
            theme_css.section("Category scores", "insights", "violet")
            score_df = pd.DataFrame(
                [
                    {"Category": col, "Score": float(row[col])}
                    for col in SCORE_COLUMNS
                    if pd.notna(row.get(col))
                ]
            )
            if score_df.empty:
                st.caption("No category scores recorded.")
            else:
                st.altair_chart(
                    alt.Chart(score_df)
                    .mark_bar(cornerRadius=6)
                    .encode(
                        y=alt.Y("Category:N", sort="-x", title=None),
                        x=alt.X("Score:Q", title=None, scale=alt.Scale(domain=[0, 10])),
                        color=alt.Color(
                            "Score:Q",
                            legend=None,
                            scale=alt.Scale(range=["#E8E4FF", "#6D5EF5"]),
                        ),
                        tooltip=["Category", "Score"],
                    )
                    .properties(height=250),
                    width="stretch",
                )
    with c2:
        with theme_css.card("d_transit"):
            theme_css.section("Commute", "directions_transit", "blue")
            for label, key in [
                ("Walk to station", "Walk to Station"),
                ("Train to city center", "Train to City Center"),
                ("Total door to door", "Total to City Center"),
            ]:
                st.markdown(f"**{label}**  \n{row.get(key) or '—'}")
            if row.get("Link"):
                st.link_button("Open listing", str(row["Link"]), icon=":material/open_in_new:")

    st.space("small")
    g1, g2 = st.columns(2)
    with g1:
        with theme_css.card("d_strengths"):
            theme_css.section("Strengths", "thumb_up", "mint")
            render_bullet_list(bullets_to_list(row.get("Strengths")))
        with theme_css.card("d_redflags"):
            theme_css.section("Red flags", "report", "rose")
            render_bullet_list(bullets_to_list(row.get("Red Flags")))
    with g2:
        with theme_css.card("d_weaknesses"):
            theme_css.section("Weaknesses", "thumb_down", "amber")
            render_bullet_list(bullets_to_list(row.get("Weaknesses")))
        with theme_css.card("d_questions"):
            theme_css.section("Questions to ask", "help", "blue")
            render_bullet_list(bullets_to_list(row.get("Questions to Ask")))


def render_compare_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No properties match the current filters.", icon=":material/filter_alt_off:")
        return

    ranked = df.sort_values("Overall", ascending=False, na_position="last").reset_index(drop=True)

    with theme_css.card("table"):
        theme_css.table_header(
            ["", "Property", "Location", "Asking price", "Gross yield", "Match score", "Verdict"]
        )

        for idx, row in ranked.iterrows():
            thumb = ensure_thumbnail(str(row["Property ID"]))
            name = html.escape(readable_property_name(row["Property ID"]))
            location = html.escape(f"{row.get('City', '')}, {row.get('State', '')}".strip(" ,"))
            region = html.escape(str(row.get("Region") or ""))
            commute = num(row.get("Commute (min)"))
            verdict = str(row.get("Recommendation") or "—")
            score = float(row["Overall"]) if pd.notna(row.get("Overall")) else 0.0
            score_pct = int(min(max(score / 10.0, 0.0), 1.0) * 100)
            vclass = theme_css.verdict_class(verdict)
            thumb_html = (
                f'<img class="pc-thumb" src="/app/static/property_thumbs/{html.escape(thumb.name)}" alt="" />'
                if thumb is not None
                else '<div class="pc-thumb"></div>'
            )
            commute_html = (
                f'<div class="pc-prop-sub">{html.escape(commute)} min to city</div>'
                if commute != "—"
                else ""
            )

            row_cols = st.columns([11.5, 0.7], gap="small", vertical_alignment="center")
            with row_cols[0]:
                st.html(
                    f"""
                    <div class="pc-table-row" style="padding-left:8px;padding-right:0;grid-template-columns:72px minmax(160px,1.6fr) minmax(110px,1fr) 100px 90px 120px 130px">
                      {thumb_html}
                      <div>
                        <div class="pc-prop-name">{name}</div>
                        <div class="pc-prop-sub">{region}</div>
                      </div>
                      <div>
                        <div class="pc-cell">{location or '—'}</div>
                        {commute_html}
                      </div>
                      <div class="pc-cell-strong">${html.escape(num(row.get('Price')))}</div>
                      <div class="pc-cell-strong">{html.escape(num(row.get('Gross yield %'), '{:.1f}'))}%</div>
                      <div class="pc-match">
                        <div class="pc-match-val">{score:.1f}</div>
                        <div class="pc-match-bar"><div class="pc-match-fill" style="width:{score_pct}%"></div></div>
                      </div>
                      <div><span class="pc-verdict {vclass}">{html.escape(verdict)}</span></div>
                    </div>
                    """
                )
            with row_cols[1]:
                if st.button(
                    "",
                    key=f"open_prop_{idx}",
                    icon=":material/more_vert:",
                    help="Open details",
                ):
                    st.session_state["compare_detail_id"] = str(row["Property ID"])

        st.html(
            f'<div class="pc-table-foot"><span>Showing {len(ranked)} of {len(ranked)} properties</span></div>'
        )

    detail_id = st.session_state.get("compare_detail_id")
    if detail_id:
        match = ranked[ranked["Property ID"] == detail_id]
        if not match.empty:
            detail_row = match.iloc[0]

            @st.dialog(readable_property_name(detail_row["Property ID"]), width="large")
            def show_detail() -> None:
                render_property_dialog(detail_row)
                if st.button("Close", key="close_compare_detail"):
                    st.session_state.pop("compare_detail_id", None)
                    st.rerun()

            show_detail()


def _map_view_state(lats: pd.Series, lons: pd.Series) -> pdk.ViewState:
    span = max(lats.max() - lats.min(), lons.max() - lons.min())
    for threshold, zoom in ((0.05, 12), (0.15, 11), (0.4, 10), (1.0, 9), (4.0, 7)):
        if span < threshold:
            break
    else:
        zoom = 4
    return pdk.ViewState(
        latitude=float(lats.mean()),
        longitude=float(lons.mean()),
        zoom=zoom,
        pitch=0,
    )


def render_map_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No properties match the current filters.", icon=":material/filter_alt_off:")
        return

    coords = cached_coordinates(tuple(df["Property ID"]))
    data = df.copy()
    data["lat"] = data["Property ID"].map(lambda p: coords.get(p, (None, None))[0])
    data["lon"] = data["Property ID"].map(lambda p: coords.get(p, (None, None))[1])
    located = data.dropna(subset=["lat", "lon"]).copy()

    if located.empty:
        st.warning(
            "None of these properties could be placed on the map. "
            "Check that `GOOGLE_MAPS_API_KEY` is set in `.env`.",
            icon=":material/location_off:",
        )
        return

    located["tip_title"] = located["Property ID"].str.replace("_", " ")
    located["tip_where"] = located["City"].astype(str) + ", " + located["State"].astype(str)
    located["tip_score"] = located["Overall"].map(lambda v: num(v, "{:.1f}"))
    located["tip_verdict"] = located["Recommendation"].fillna("—").astype(str)
    located["tip_price"] = located["Price"].map(lambda v: "$" + num(v))
    located["tip_rent"] = located["Estimated Rent"].map(lambda v: "$" + num(v))
    located["tip_yield"] = located["Gross yield %"].map(lambda v: num(v, "{:.1f}") + "%")
    located["tip_commute"] = located["Commute (min)"].map(lambda v: num(v) + " min")
    located["color"] = located["Recommendation"].map(
        lambda r: REC_COLORS.get(str(r), DEFAULT_REC_COLOR)
    )
    located["radius"] = 90 + located["Overall"].fillna(0) * 28

    layer = pdk.Layer(
        "ScatterplotLayer",
        id="properties",
        data=located[
            [
                "Property ID", "lat", "lon", "color", "radius",
                "tip_title", "tip_where", "tip_score", "tip_verdict",
                "tip_price", "tip_rent", "tip_yield", "tip_commute",
            ]
        ],
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius="radius",
        radius_min_pixels=9,
        radius_max_pixels=34,
        stroked=True,
        get_line_color=[255, 255, 255],
        line_width_min_pixels=2,
        pickable=True,
        auto_highlight=True,
    )

    tooltip = {
        "html": """
            <div style="font-family:'Plus Jakarta Sans',sans-serif;min-width:210px">
              <div style="font-size:13px;font-weight:800;color:#2B2D42;margin-bottom:2px">
                {tip_title}
              </div>
              <div style="font-size:11px;color:#8891AF;margin-bottom:8px">
                {tip_where} &middot; {tip_verdict}
              </div>
              <div style="font-size:20px;font-weight:800;color:#6D5EF5;line-height:1">
                {tip_score}<span style="font-size:12px;color:#8891AF">/10</span>
              </div>
              <div style="margin-top:8px;font-size:12px;color:#3A3E5C;line-height:1.65">
                Price <b>{tip_price}</b><br/>
                Rent <b>{tip_rent}</b>/mo &middot; yield <b>{tip_yield}</b><br/>
                Commute <b>{tip_commute}</b>
              </div>
            </div>
        """,
        "style": {
            "backgroundColor": "#F4F6FC",
            "borderRadius": "18px",
            "padding": "14px 16px",
            "boxShadow": "10px 10px 24px rgba(120,132,165,.35), -6px -6px 16px #FFFFFF",
            "border": "none",
        },
    }

    with theme_css.card("map"):
        theme_css.section(
            "Where they are — hover a dot for details, click to open it",
            "map", "violet",
        )
        event = st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=_map_view_state(located["lat"], located["lon"]),
                map_provider="carto",
                map_style=pdk.map_styles.CARTO_LIGHT,
                tooltip=tooltip,
            ),
            height=540,
            on_select="rerun",
            selection_mode="single-object",
            key="property_map",
        )
        theme_css.chips(
            [f"{rec} — {int((located['Recommendation'] == rec).sum())}" for rec in RECOMMENDATIONS]
        )
        missing = len(data) - len(located)
        if missing:
            st.caption(f"{missing} property(ies) could not be geocoded and are not shown.")

    picked = (event or {}).get("selection", {}).get("objects", {}).get("properties") or []
    if picked:
        match = df[df["Property ID"] == picked[0].get("Property ID")]
        if not match.empty:
            row = match.iloc[0]

            @st.dialog(str(row["Property ID"]), width="large")
            def show_map_detail() -> None:
                render_property_dialog(row)

            show_map_detail()


def render_charts_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No properties match the current filters.", icon=":material/filter_alt_off:")
        return

    c1, c2 = st.columns(2, gap="medium")

    with c1:
        with theme_css.card("c_value"):
            theme_css.section("Value map — price vs match", "scatter_plot", "violet")
            data = df.dropna(subset=["Price", "Overall"])
            if data.empty:
                st.caption("Not enough price and score data yet.")
            else:
                st.altair_chart(
                    alt.Chart(data)
                    .mark_circle(opacity=0.85, stroke="white", strokeWidth=1.5)
                    .encode(
                        x=alt.X("Price:Q", title="Asking price ($)"),
                        y=alt.Y("Overall:Q", title="Match score", scale=alt.Scale(domain=[0, 10])),
                        size=alt.Size("Gross yield %:Q", legend=None, scale=alt.Scale(range=[80, 500])),
                        color=alt.Color("Recommendation:N", title=None,
                                        legend=alt.Legend(orient="bottom")),
                        tooltip=["Property ID", "City", "Price", "Overall",
                                 alt.Tooltip("Gross yield %", format=".1f")],
                    )
                    .properties(height=CHART_HEIGHT),
                    width="stretch",
                )

    with c2:
        with theme_css.card("c_commute"):
            theme_css.section("Commute vs match", "commute", "blue")
            data = df.dropna(subset=["Commute (min)", "Overall"])
            if data.empty:
                st.caption("No commute data yet — re-run analysis to populate transit times.")
            else:
                st.altair_chart(
                    alt.Chart(data)
                    .mark_circle(opacity=0.85, stroke="white", strokeWidth=1.5, size=220)
                    .encode(
                        x=alt.X("Commute (min):Q", title="Door to city center (minutes)"),
                        y=alt.Y("Overall:Q", title="Match score", scale=alt.Scale(domain=[0, 10])),
                        color=alt.Color("Recommendation:N", title=None,
                                        legend=alt.Legend(orient="bottom")),
                        tooltip=["Property ID", "Commute (min)", "Overall"],
                    )
                    .properties(height=CHART_HEIGHT),
                    width="stretch",
                )

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        with theme_css.card("c_top"):
            theme_css.section("Leaderboard", "leaderboard", "mint")
            top = df.nlargest(10, "Overall")[["Property ID", "Overall", "Price"]]
            if top.empty:
                st.caption("No scores yet.")
            else:
                st.altair_chart(
                    alt.Chart(top)
                    .mark_bar(cornerRadiusEnd=8)
                    .encode(
                        y=alt.Y("Property ID:N", sort="-x", title=None),
                        x=alt.X("Overall:Q", title="Match score", scale=alt.Scale(domain=[0, 10])),
                        color=alt.Color("Overall:Q", legend=None,
                                        scale=alt.Scale(range=["#E8E4FF", "#6D5EF5"])),
                        tooltip=["Property ID", "Overall", "Price"],
                    )
                    .properties(height=CHART_HEIGHT),
                    width="stretch",
                )

    with c4:
        with theme_css.card("c_avg"):
            theme_css.section("Where this set is strong", "radar", "amber")
            avgs = [
                {"Category": col, "Score": df[col].mean()}
                for col in SCORE_COLUMNS
                if col in df.columns and df[col].notna().any()
            ]
            if not avgs:
                st.caption("No category scores yet.")
            else:
                st.altair_chart(
                    alt.Chart(pd.DataFrame(avgs))
                    .mark_bar(cornerRadiusEnd=8)
                    .encode(
                        x=alt.X("Category:N", sort="-y", title=None,
                                axis=alt.Axis(labelAngle=-35)),
                        y=alt.Y("Score:Q", title="Average", scale=alt.Scale(domain=[0, 10])),
                        color=alt.Color("Score:Q", legend=None,
                                        scale=alt.Scale(range=["#E6F4F1", "#3D9B8F"])),
                        tooltip=["Category", alt.Tooltip("Score", format=".1f")],
                    )
                    .properties(height=CHART_HEIGHT),
                    width="stretch",
                )


def render_head_to_head_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No properties match the current filters.", icon=":material/filter_alt_off:")
        return

    with theme_css.card("h2h_pick"):
        theme_css.section("Pick 2–4 properties to compare", "compare_arrows", "violet")
        selected = st.multiselect(
            "Properties",
            options=df["Property ID"].tolist(),
            max_selections=4,
            placeholder="Choose properties…",
            label_visibility="collapsed",
        )

    if len(selected) < 2:
        st.caption("Select at least two properties to see the head-to-head view.")
        return

    subset = df[df["Property ID"].isin(selected)]
    accents = ["violet", "mint", "peach", "blue"]

    for idx, (col, (_, row), accent) in enumerate(
        zip(st.columns(len(subset), gap="medium"), subset.iterrows(), accents)
    ):
        with col:
            with theme_css.card(f"h2h_{idx}"):
                theme_css.kpi(
                    str(row.get("City", "")) or "Property",
                    f"{num(row.get('Overall'), '{:.1f}')}/10",
                    "home",
                    accent,
                    str(row["Property ID"])[:26],
                )
                st.markdown(
                    f"- **Price:** {format_currency(row.get('Price'))}\n"
                    f"- **Rent/mo:** {format_currency(row.get('Estimated Rent'))}\n"
                    f"- **Yield:** {num(row.get('Gross yield %'), '{:.1f}')}%\n"
                    f"- **Net/mo:** {format_currency(row.get('Net monthly'))}\n"
                    f"- **Commute:** {num(row.get('Commute (min)'))} min\n"
                    f"- **Verdict:** {row.get('Recommendation', '—')}"
                )

    long_rows = [
        {"Property ID": row["Property ID"], "Category": col, "Score": float(row[col])}
        for _, row in subset.iterrows()
        for col in SCORE_COLUMNS
        if pd.notna(row.get(col))
    ]
    if long_rows:
        with theme_css.card("h2h_chart"):
            theme_css.section("Category by category", "bar_chart", "blue")
            st.altair_chart(
                alt.Chart(pd.DataFrame(long_rows))
                .mark_bar(cornerRadiusEnd=5)
                .encode(
                    x=alt.X("Category:N", title=None, axis=alt.Axis(labelAngle=-30)),
                    y=alt.Y("Score:Q", title="Score", scale=alt.Scale(domain=[0, 10])),
                    color=alt.Color("Property ID:N", title=None,
                                    legend=alt.Legend(orient="bottom")),
                    xOffset=alt.XOffset("Property ID:N"),
                    tooltip=["Property ID", "Category", "Score"],
                )
                .properties(height=340),
                width="stretch",
            )


def render_notes_tab(df: pd.DataFrame, original: pd.DataFrame) -> None:
    if df.empty:
        st.info("No properties match the current filters.", icon=":material/filter_alt_off:")
        return

    notes_df = df[NOTES_COLUMNS].copy()
    notes_df["Wow Factor"] = pd.to_numeric(notes_df["Wow Factor"], errors="coerce")
    notes_df["Visit Date"] = pd.to_datetime(notes_df["Visit Date"], errors="coerce")
    for col in ("Notes", "Final Decision"):
        notes_df[col] = notes_df[col].fillna("").astype(str).replace("nan", "")

    with theme_css.card("notes"):
        theme_css.section("Your own scoring and follow-up", "edit_note", "mint")
        st.caption(
            "These four columns are yours — the AI never overwrites them. "
            "Edit below, then save back to the Sheet."
        )
        edited = st.data_editor(
            notes_df,
            column_config={
                "Property ID": st.column_config.TextColumn("Property", disabled=True),
                "Region": st.column_config.TextColumn("Region", disabled=True, width="small"),
                "_sheet_row": None,
                "Wow Factor": st.column_config.NumberColumn(
                    "Wow factor", min_value=0, max_value=10, step=1, format="%d"
                ),
                "Notes": st.column_config.TextColumn("Notes", width="large"),
                "Visit Date": st.column_config.DateColumn("Visit date", format="YYYY-MM-DD"),
                "Final Decision": st.column_config.SelectboxColumn(
                    "Decision", options=["", *FINAL_DECISIONS], width="small"
                ),
            },
            hide_index=True,
            height=420,
            key="notes_editor",
        )

        if st.button("Save to Google Sheets", type="primary", icon=":material/cloud_upload:"):
            orig_map = original.set_index(["Region", "Property ID"])
            changes = []
            for _, row in edited.iterrows():
                key = (row["Region"], row["Property ID"])
                if key not in orig_map.index:
                    continue
                orig_row = orig_map.loc[key]
                if isinstance(orig_row, pd.DataFrame):
                    orig_row = orig_row.iloc[0]
                for col in PERSONAL_COLUMN_LIST:
                    old = str(orig_row.get(col, "") or "").strip()
                    new = str(row.get(col, "") or "").strip()
                    if col == "Visit Date":
                        old, new = old[:10], new[:10]
                    if old != new:
                        changes.append(row)
                        break

            if not changes:
                st.toast("Nothing changed.", icon=":material/info:")
                return
            try:
                count = save_personal_edits(pd.DataFrame(changes))
                st.success(f"Saved {count} row(s) to Google Sheets.", icon=":material/check_circle:")
                cached_load_properties.clear()
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Save failed: {exc}", icon=":material/error:")


# --- Page ---

theme_css.hero(
    "Property comparison",
    "All your properties, ranked and compared.",
)

all_regions = list_regions()

try:
    raw = cached_load_properties(tuple(all_regions))
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not load your Google Sheet: {exc}", icon=":material/cloud_off:")
    st.link_button("Open Google Sheets", sheet_url(), icon=":material/open_in_new:")
    st.stop()

if raw.empty:
    st.info(
        "No properties in your Sheet yet — analyze a listing first.",
        icon=":material/inbox:",
    )
    st.link_button("Open Google Sheets", sheet_url(), icon=":material/open_in_new:")
    st.stop()

with st.sidebar:
    theme_css.section("Filters", "apartment", "violet")
    region_filter = st.multiselect("Regions", options=all_regions, default=all_regions)

    prices = raw["Price"].dropna()
    if not prices.empty and prices.max() > prices.min():
        price_min, price_max = st.slider(
            "Price range",
            min_value=float(prices.min()),
            max_value=float(prices.max()),
            value=(float(prices.min()), float(prices.max())),
            format="$%d",
        )
    else:
        price_min, price_max = 0.0, float(prices.max()) if not prices.empty else 1e9

    min_overall = st.slider("Minimum match score", 0.0, 10.0, 0.0, 0.5)
    max_commute_val = st.slider(
        "Max commute (minutes)", 0, 180, 180,
        help="180 keeps everything, including properties with no commute data.",
    )
    max_commute: float | None = float(max_commute_val) if max_commute_val < 180 else None
    min_beds = st.slider("Minimum bedrooms", 0, 6, 0)

    st.caption("Verdict")
    rec_selected: list[str] = []
    for rec in RECOMMENDATIONS:
        if st.checkbox(rec, value=True, key=f"verdict_{rec}"):
            rec_selected.append(rec)

    st.space("small")
    if st.button("Reset filters", icon=":material/restart_alt:", width="stretch"):
        for rec in RECOMMENDATIONS:
            st.session_state[f"verdict_{rec}"] = True
        st.rerun()
    st.link_button(
        "Open Google Sheets", sheet_url(),
        icon=":material/open_in_new:", width="stretch",
    )
    if st.button("Refresh from Sheets", icon=":material/sync:", width="stretch"):
        cached_load_properties.clear()
        st.rerun()

filtered = apply_filters(
    raw,
    regions=region_filter,
    recommendations=rec_selected,
    price_range=(price_min, price_max),
    min_overall=min_overall,
    max_commute=max_commute,
    min_beds=min_beds,
)

active_chips = list(region_filter or [])
if min_overall > 0:
    active_chips.append(f"Match ≥ {min_overall:g}")
if max_commute is not None:
    active_chips.append(f"≤ {int(max_commute)} min")
if min_beds > 0:
    active_chips.append(f"{min_beds}+ beds")
active_chips.append(f"{len(filtered)} properties")
theme_css.chips(active_chips)

render_kpis(filtered)
st.space("small")

# Lazy tabs: only the open tab runs, so a stale selection in another tab
# can never open a second dialog on the same rerun.
tab_table, tab_map, tab_charts, tab_h2h, tab_notes = st.tabs(
    [
        ":material/table_rows: Compare",
        ":material/map: Map",
        ":material/insights: Charts",
        ":material/compare_arrows: Head-to-head",
        ":material/edit_note: My notes",
    ],
    on_change="rerun",
    key="compare_tabs",
)

if tab_table.open:
    with tab_table:
        render_compare_table(filtered)

if tab_map.open:
    with tab_map:
        render_map_tab(filtered)

if tab_charts.open:
    with tab_charts:
        render_charts_tab(filtered)

if tab_h2h.open:
    with tab_h2h:
        render_head_to_head_tab(filtered)

if tab_notes.open:
    with tab_notes:
        render_notes_tab(filtered, raw)
