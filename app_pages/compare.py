"""Compare page: portfolio dashboard from Google Sheets."""

from __future__ import annotations

import html
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

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
from flood_lookup import FLOOD_GATE_VERSION  # noqa: E402
from neighbourhood_tiers import RULES_VERSION, neighbourhood_search_tier  # noqa: E402
from scoring import (  # noqa: E402
    PERSONAL_MATCH_WEIGHT,
    compute_overall,
    parse_weights,
    wow_factor_value,
)
from sheets_data import (  # noqa: E402
    PERSONAL_COLUMN_LIST,
    SCORE_COLUMNS,
    add_derived_columns,
    load_properties,
    personal_note_text,
    save_personal_edits,
)
from ui_helpers import (  # noqa: E402
    bullets_to_list,
    format_currency,
    normalize_listing_url,
    property_title_html,
    show_neighbourhood_dialog,
    show_judgment_dialog,
    show_property_note_dialog,
    rationale_to_bullets,
    render_bullet_list,
)
from utils import load_strategy_raw_for_region  # noqa: E402
from contacted import contacted_ids, contingent_ids, toggle_contacted, toggle_contingent  # noqa: E402
from compare_table import (  # noqa: E402
    COMPARE_TABLE_HEADERS,
    annual_tax_label,
    default_sort_ascending,
    hood_badge_html,
    neighbourhood_label,
    num,
    render_table_html,
    sort_compare_dataframe,
)
from neighbourhood_tiers import score_note_10, tier_short_label  # noqa: E402
from write_to_sheets import list_regions, sheet_url  # noqa: E402

RECOMMENDATIONS = ["Reject", "Save", "Worth visiting"]
FINAL_DECISIONS = ["Visit", "Reject", "Pursue", "Maybe", "Pass", "Visited", "Offer made"]
ALL_PROPERTIES_TAB = "All properties"
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

# Matches sheets_data._verdict_label — sort by what the Verdict column shows.
_VERDICT_ORDER = {
    "Buy": 0,
    "Strong candidate": 1,
    "Investigate": 2,
    "Pass": 3,
    "Worth visiting": 1,
    "Save": 2,
    "Reject": 3,
}


def _sheets_cache_generation() -> int:
    return int(st.session_state.get("sheets_cache_generation", 0))


@st.cache_data(ttl="10m", show_spinner="Loading properties from Google Sheets…")
def cached_load_properties(
    regions: tuple[str, ...],
    _generation: int,
    _hood_rules: int,
    _flood_gate: int,
) -> pd.DataFrame:
    del _generation, _hood_rules, _flood_gate  # bust cache after refresh or rule changes
    return load_properties(list(regions))


@st.cache_data(ttl="24h", show_spinner="Locating properties…")
def cached_coordinates(property_ids: tuple[str, ...]) -> dict[str, tuple[float, float]]:
    return coordinates_for(list(property_ids))


def _sync_compare_sort() -> tuple[str, bool]:
    qp_sort = st.query_params.get("compare_sort")
    qp_dir = st.query_params.get("compare_dir")
    if qp_sort:
        st.session_state["compare_sort"] = str(qp_sort)
        st.session_state["compare_sort_asc"] = str(qp_dir or "desc").lower() == "asc"
    sort_key = str(st.session_state.get("compare_sort", "overall"))
    ascending = bool(st.session_state.get("compare_sort_asc", False))
    return sort_key, ascending


def _default_sort_ascending(sort_key: str) -> bool:
    return sort_key in {"property", "location", "trailer", "transit_now", "transit_future", "verdict"}


def _compare_nav_href(**extra: str) -> str:
    sort_key, sort_asc = _sync_compare_sort()
    params: dict[str, str] = {
        "compare_sort": sort_key,
        "compare_dir": "asc" if sort_asc else "desc",
    }
    for key, value in extra.items():
        if value:
            params[key] = value
    return "?" + urllib.parse.urlencode(params)


def _sort_header_link(
    label: str,
    sort_key: str,
    *,
    sticky: bool = False,
    sticky_end: bool = False,
) -> str:
    active_key, active_asc = _sync_compare_sort()
    is_active = active_key == sort_key
    arrow = (" ▲" if active_asc else " ▼") if is_active else ""
    if is_active:
        next_asc = not active_asc
    else:
        next_asc = default_sort_ascending(sort_key)
    params: dict[str, str] = {
        "compare_sort": sort_key,
        "compare_dir": "asc" if next_asc else "desc",
    }
    detail = st.query_params.get("detail")
    if detail:
        params["detail"] = str(detail)
    href = "?" + urllib.parse.urlencode(params)
    cls = "pc-sort-link"
    if is_active:
        cls += " pc-sort-active"
    if sticky:
        cls += " pc-sticky-prop pc-sticky-head"
    if sticky_end:
        cls += " pc-verdict-col pc-verdict-head"
    inner = f"{html.escape(label)}{arrow}"
    return f'<a class="{cls}" href="{html.escape(href)}">{inner}</a>'


def render_match_score_breakdown(row: pd.Series) -> None:
    """Category scores and weighted contributions for the overall match."""
    region = str(row.get("Region") or "").strip() or None
    try:
        weights = parse_weights(load_strategy_raw_for_region(region))
    except ValueError as exc:
        st.warning(f"Could not load strategy weights: {exc}")
        weights = {}

    overall = row.get("Overall")
    overall_label = f"{float(overall):.2f}/10" if pd.notna(overall) else "—"
    match_100 = row.get("Match /100")
    match_label = f"{float(match_100):.0f}/100" if pd.notna(match_100) else "—"
    ai_overall = row.get("Overall AI")
    ai_label = f"{float(ai_overall):.2f}/10" if pd.notna(ai_overall) else "—"
    yours = wow_factor_value(row.get("Wow Factor"))

    rec = str(row.get("Recommendation") or "—")
    st.markdown(f"**Match (displayed):** {overall_label} ({match_label}) · **{rec}**")
    if yours is not None and pd.notna(ai_overall):
        pct = int(round(PERSONAL_MATCH_WEIGHT * 100))
        st.caption(
            f"AI match **{ai_label}** + your **{yours:g}/10** "
            f"({100 - pct}% / {pct}% blend) → **{overall_label}**."
        )
    elif pd.notna(ai_overall):
        st.caption(f"AI match **{ai_label}**. Set **Your /10** in the table to blend in your score.")
    hood = neighbourhood_label(row)
    tier = row.get("Neighbourhood tier")
    tier_label = tier_short_label(int(tier)) if pd.notna(tier) else "unranked"
    area_app = str(row.get("Appreciation label") or "—")
    area_rent = str(row.get("Rental potential") or "—")
    prop_app = score_note_10(float(row["Appreciation"])) if pd.notna(row.get("Appreciation")) else "—"
    prop_rent = score_note_10(float(row["Rental"])) if pd.notna(row.get("Rental")) else "—"
    prop_loc = score_note_10(float(row["Location"])) if pd.notna(row.get("Location")) else "—"
    st.caption(
        f"**{hood}** ({tier_label.lower()}) — table columns **Area appr.** / **Area rental** "
        f"show neighbourhood benchmarks ({area_app}, {area_rent}). "
        f"This breakdown uses **property** scores from analysis "
        f"(appreciation {prop_app}, rental {prop_rent}, location {prop_loc}). "
        "**Location** is commute, transit, and amenities for this listing, not the neighbourhood colour alone."
    )
    st.caption(
        "Overall = sum of (category score × weight). Weights come from your strategy for this region."
    )

    note = personal_note_text(row.get("Notes"))
    with theme_css.card("match_personal_note"):
        theme_css.section("Your rating", "edit_note", "mint")
        if yours is not None:
            st.markdown(f"**Your score:** {yours:g}/10")
        else:
            st.caption("No personal /10 yet — use **Your /10** in the table.")
        if note:
            st.markdown(note)
        pid = str(row["Property ID"])
        if st.button("Edit your /10 and note", key=f"edit_note_from_match_{pid}"):
            st.query_params["note"] = pid
            st.query_params.pop("scores", None)
            st.rerun()

    rows: list[dict[str, object]] = []
    weighted_sum = 0.0
    for col in SCORE_COLUMNS:
        score = row.get(col)
        if pd.isna(score):
            continue
        score_f = float(score)
        wkey = col.lower()
        weight = float(weights.get(wkey, 0.0)) if weights else 0.0
        contrib = score_f * weight
        weighted_sum += contrib
        rows.append(
            {
                "Category": col,
                "Score": score_f,
                "Weight %": round(weight * 100, 1),
                "Contribution": round(contrib, 2),
            }
        )

    if not rows:
        st.info("No category scores on file for this property.", icon=":material/info:")
        return

    breakdown = pd.DataFrame(rows).sort_values("Contribution", ascending=False)
    st.dataframe(
        breakdown,
        column_config={
            "Score": st.column_config.NumberColumn(format="%.1f"),
            "Weight %": st.column_config.NumberColumn(format="%.1f"),
            "Contribution": st.column_config.NumberColumn(format="%.2f"),
        },
        hide_index=True,
        width="stretch",
    )

    if weights and not row.get("Climate cap"):
        try:
            cats = {c.lower(): float(row[c]) for c in SCORE_COLUMNS if pd.notna(row.get(c))}
            if len(cats) == len(weights):
                recomputed = compute_overall(cats, weights)
                st.caption(f"Recomputed from categories: **{recomputed:.2f}/10**")
        except (ValueError, TypeError):
            pass
    if row.get("Climate cap"):
        st.caption(
            "Climate resilience is 1/10 because of flood exposure. "
            "That caps the match score at 4.0, so a high appreciation score cannot carry the listing."
        )

    detail_href = _compare_nav_href(detail=str(row["Property ID"]))
    st.markdown(f"[Full property details]({detail_href})")


def _load_scored_from_disk(property_id: str) -> dict[str, Any]:
    path = ROOT / "properties" / str(property_id) / "latest.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    scored = data.get("scored")
    return scored if isinstance(scored, dict) else {}


def _verdict_derivation_note(
    verdict: str,
    recommendation: str,
    overall: float | None,
    *,
    flood_gate: bool = False,
    climate_cap: bool = False,
) -> str:
    rec = (recommendation or "").strip()
    score_txt = f"{overall:.1f}/10" if overall is not None else "—"
    if climate_cap and verdict == "Pass":
        return (
            f"**{verdict}** because climate resilience is **1/10** (flood exposure). "
            f"The match score is capped at **{score_txt}**."
        )
    if flood_gate and verdict == "Pass":
        return (
            f"**{verdict}** because this pin is in a mapped flood zone. "
            f"Climate and risk were capped and the match score was recomputed (**{score_txt}**)."
        )
    if verdict == "Buy":
        return (
            f"**{verdict}** = model said **Worth visiting** and match score is **{score_txt}** (8.0 or higher)."
        )
    if verdict == "Strong candidate":
        return (
            f"**{verdict}** = **Worth visiting** with match **{score_txt}** below the 8.0 “Buy” threshold."
        )
    if verdict == "Investigate":
        return f"**{verdict}** = model recommendation **Save** (worth a closer look; match **{score_txt}**)."
    if verdict == "Pass":
        return f"**{verdict}** = model recommendation **Reject** (match **{score_txt}**)."
    if rec:
        return f"Display label **{verdict}** from recommendation **{rec}** (match **{score_txt}**)."
    return f"Match score **{score_txt}**."


def render_verdict_explanation(row: pd.Series) -> None:
    pid = str(row["Property ID"])
    verdict = str(row.get("Verdict") or "—")
    rec = str(row.get("Recommendation") or "—")
    overall = float(row["Overall"]) if pd.notna(row.get("Overall")) else None

    scored = _load_scored_from_disk(pid)
    rationale = str(scored.get("rationale") or "").strip()

    flood_gate = bool(row.get("Flood gate"))
    climate_cap = bool(row.get("Climate cap"))
    st.markdown(
        _verdict_derivation_note(
            verdict, rec, overall, flood_gate=flood_gate, climate_cap=climate_cap
        )
    )
    st.caption(
        "Verdict labels map the model’s Reject / Save / Worth visiting plus your match score. "
        "Narrative below is from the analysis run (same as Analyze)."
    )

    if rationale:
        st.markdown("**Why this recommendation**")
        render_bullet_list(rationale_to_bullets(rationale))
    else:
        st.info(
            "No saved rationale text for this property (older Sheet row or analysis run missing). "
            "Strengths and flags below are from the Sheet.",
            icon=":material/info:",
        )

    strengths = scored.get("strengths") or bullets_to_list(row.get("Strengths"))
    weaknesses = scored.get("weaknesses") or bullets_to_list(row.get("Weaknesses"))
    red_flags = scored.get("red_flags") or bullets_to_list(row.get("Red Flags"))
    questions = scored.get("questions_to_ask") or bullets_to_list(row.get("Questions to Ask"))

    if strengths:
        st.markdown("**Strengths**")
        render_bullet_list(strengths)
    if weaknesses:
        st.markdown("**Weaknesses**")
        render_bullet_list(weaknesses)
    if red_flags:
        st.markdown("**Red flags**")
        render_bullet_list(red_flags)
    if questions:
        st.markdown("**Questions to ask**")
        render_bullet_list(questions)

    st.markdown(
        f"[Match score breakdown]({_compare_nav_href(scores=pid)}) · "
        f"[Full property details]({_compare_nav_href(detail=pid)})"
    )


def apply_filters(
    df: pd.DataFrame,
    *,
    regions: list[str],
    recommendations: list[str],
    price_range: tuple[float, float],
    min_overall: float,
    max_commute: float | None,
    min_beds: int,
    hide_rejected: bool = False,
) -> pd.DataFrame:
    out = df.copy()
    if hide_rejected and "Final Decision" in out.columns:
        labels = out["Final Decision"].fillna("").astype(str).str.strip()
        out = out[labels.str.casefold() != "reject"]
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
    link = normalize_listing_url(row.get("Link"))
    title = readable_property_name(row["Property ID"])
    if link:
        st.link_button(
            title,
            link,
            icon=":material/open_in_new:",
            width="stretch",
        )
    else:
        st.markdown(f"**{html.escape(title)}**")
        st.caption("No listing URL on file — re-analyze with the Zillow link filled in.")

    photo_path = find_property_photo(str(row["Property ID"]))
    if photo_path is not None:
        left, right = st.columns([1.1, 1.4], gap="large")
        with left:
            st.image(str(photo_path), width="stretch")
        with right:
            theme_css.chip_row(
                hood_badge_html(row, href=_compare_nav_href(hood=neighbourhood_label(row))),
                f'<span class="pc-chip">{html.escape(str(row.get("Recommendation", "")))}</span>',
                f'<span class="pc-chip">Overall {html.escape(num(row.get("Overall"), "{:.1f}"))}/10</span>',
                f'<span class="pc-chip">{html.escape(str(row.get("Region", "")))}</span>',
            )
            theme_css.kpi_grid(
                [
                    ("Price", "$" + num(row.get("Price")), "sell", "peach", ""),
                    ("Rent / mo", "$" + num(row.get("Estimated Rent")), "savings", "mint", ""),
                    ("Annual tax", annual_tax_label(row), "receipt_long", "amber", ""),
                    ("Gross yield", num(row.get("Gross yield %"), "{:.1f}") + "%", "percent", "violet", ""),
                    ("Commute", num(row.get("Commute (min)")) + " min", "train", "blue", ""),
                ],
                min_width="150px",
            )
    else:
        theme_css.chip_row(
            hood_badge_html(row, href=_compare_nav_href(hood=neighbourhood_label(row))),
            f'<span class="pc-chip">{html.escape(str(row.get("Recommendation", "")))}</span>',
            f'<span class="pc-chip">Overall {html.escape(num(row.get("Overall"), "{:.1f}"))}/10</span>',
            f'<span class="pc-chip">{html.escape(str(row.get("Region", "")))}</span>',
        )
        theme_css.kpi_grid(
            [
                ("Price", "$" + num(row.get("Price")), "sell", "peach", ""),
                ("Rent / mo", "$" + num(row.get("Estimated Rent")), "savings", "mint", ""),
                ("Annual tax", annual_tax_label(row), "receipt_long", "amber", ""),
                ("Gross yield", num(row.get("Gross yield %"), "{:.1f}") + "%", "percent", "violet", ""),
                ("Commute", num(row.get("Commute (min)")) + " min", "train", "blue", ""),
            ],
            min_width="170px",
        )

    note = personal_note_text(row.get("Notes"))
    yours_detail = wow_factor_value(row.get("Wow Factor"))
    with theme_css.card("d_overall_note"):
        theme_css.section("Your rating", "edit_note", "mint")
        if yours_detail is not None:
            st.markdown(f"**Your score:** {yours_detail:g}/10 (blends into Match)")
        if note:
            st.markdown(note)
        elif yours_detail is None:
            st.caption("Set **Your /10** in the table — optional note explains why.")
        if st.button("Edit your /10 and note", key=f"edit_note_from_detail_{row['Property ID']}"):
            st.query_params["note"] = str(row["Property ID"])
            st.query_params.pop("detail", None)
            st.rerun()

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
                ("Walk to stop / station", "Walk to Station"),
                ("Transit to Downtown", "Train to City Center"),
                ("Door to door (Downtown)", "Total to City Center"),
            ]:
                st.markdown(f"**{label}**  \n{row.get(key) or '—'}")
            plan = str(row.get("Transit Plan Detail") or "").strip()
            if plan:
                st.markdown("**Future transit (research)**")
                st.markdown(plan)
            elif str(row.get("Future Transit") or "").strip():
                st.caption(f"Future: {row.get('Future Transit')}")
            if row.get("Link"):
                st.link_button("Open listing", str(row["Link"]), icon=":material/open_in_new:")

    st.space("small")
    theme_css.render_market_research_sections(row)

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

    sort_key, sort_asc = _sync_compare_sort()
    ranked = sort_compare_dataframe(df, sort_key, ascending=sort_asc).reset_index(drop=True)

    with theme_css.card("table"):
        st.caption(
            "Click a column header to sort (click again to reverse). "
            "Click a neighbourhood for area context. **Area appr.** / **Area rental** are neighbourhood "
            "benchmarks; match score uses property-specific category scores (see match breakdown). "
            "Check **Contacted** after you reach the agent, and **Contingent** if the listing goes under contract. "
            "**Your /10** blends into Match (80% AI + 20% you when set). **Judgment** = Visit or Reject "
            "(hover for reason). "
            "Click **Match** or **Verdict** for score breakdown and recommendation rationale. "
            "Est. net yield is (annual rent − annual tax − insurance − HOA×12) ÷ price."
        )
        st.html(
            render_table_html(
                ranked,
                headers=COMPARE_TABLE_HEADERS,
                sort_key=sort_key,
                sort_asc=sort_asc,
                href_builder=_compare_nav_href,
                contacted_ids=contacted_ids(),
                contacted_href=lambda pid: _compare_nav_href(contacted=pid),
                contingent_ids=contingent_ids(),
                contingent_href=lambda pid: _compare_nav_href(contingent=pid),
                note_href=lambda pid: _compare_nav_href(note=pid),
                judgment_href=lambda pid: _compare_nav_href(judgment=pid),
            )
        )
        st.html(
            f'<div class="pc-table-foot"><span>Showing {len(ranked)} of {len(ranked)} properties</span></div>'
        )

    verdict_id = st.query_params.get("verdict")
    if verdict_id:
        verdict_match = ranked[ranked["Property ID"] == verdict_id]
        if not verdict_match.empty:
            verdict_row = verdict_match.iloc[0]

            @st.dialog(
                f"Verdict — {readable_property_name(verdict_row['Property ID'])}",
                width="large",
            )
            def show_verdict() -> None:
                render_verdict_explanation(verdict_row)
                if st.button("Close", key="close_compare_verdict"):
                    st.query_params.pop("verdict", None)
                    st.rerun()

            show_verdict()

    scores_id = st.query_params.get("scores")
    if scores_id:
        score_match = ranked[ranked["Property ID"] == scores_id]
        if not score_match.empty:
            score_row = score_match.iloc[0]

            @st.dialog(
                f"Match score — {readable_property_name(score_row['Property ID'])}",
                width="large",
            )
            def show_scores() -> None:
                render_match_score_breakdown(score_row)
                if st.button("Close", key="close_compare_scores"):
                    st.query_params.pop("scores", None)
                    st.rerun()

            show_scores()

    detail_id = st.query_params.get("detail") or st.session_state.get("compare_detail_id")
    if detail_id:
        match = ranked[ranked["Property ID"] == detail_id]
        if not match.empty:
            detail_row = match.iloc[0]

            @st.dialog(readable_property_name(detail_row["Property ID"]), width="large")
            def show_detail() -> None:
                render_property_dialog(detail_row)
                if st.button("Close", key="close_compare_detail"):
                    st.session_state.pop("compare_detail_id", None)
                    st.query_params.pop("detail", None)
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
    for col in ("Notes", "Final Decision", "Judgment reason"):
        notes_df[col] = notes_df[col].fillna("").astype(str).replace("nan", "")

    with theme_css.card("notes"):
        theme_css.section("Your own scoring and follow-up", "edit_note", "mint")
        st.caption(
            "These personal columns are yours — the AI never overwrites them. "
            "Edit below, then save back to the Sheet."
        )
        edited = st.data_editor(
            notes_df,
            column_config={
                "Property ID": st.column_config.TextColumn("Property", disabled=True),
                "Region": st.column_config.TextColumn("Region", disabled=True, width="small"),
                "_sheet_row": None,
                "Wow Factor": st.column_config.NumberColumn(
                    "Your /10", min_value=0, max_value=10, step=0.5, format="%.1f"
                ),
                "Notes": st.column_config.TextColumn("Note (optional)", width="large"),
                "Judgment reason": st.column_config.TextColumn("Judgment reason", width="large"),
                "Visit Date": st.column_config.DateColumn("Visit date", format="YYYY-MM-DD"),
                "Final Decision": st.column_config.SelectboxColumn(
                    "Judgment (Visit / Reject)",
                    options=["", *FINAL_DECISIONS],
                    width="medium",
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
                count, save_errors = save_personal_edits(pd.DataFrame(changes))
                for msg in save_errors:
                    st.warning(msg, icon=":material/warning:")
                if count:
                    st.success(
                        f"Saved {count} row(s) to Google Sheets.",
                        icon=":material/check_circle:",
                    )
                    cached_load_properties.clear()
                    st.rerun()
                elif save_errors:
                    st.error(
                        "No rows were saved. Fix the issues above and try again.",
                        icon=":material/error:",
                    )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Save failed: {exc}", icon=":material/error:")


# --- Page ---

_pending_contacted = st.query_params.get("contacted")
if _pending_contacted:
    toggle_contacted(str(_pending_contacted))
    st.query_params.pop("contacted", None)
    st.rerun()

_pending_contingent = st.query_params.get("contingent")
if _pending_contingent:
    toggle_contingent(str(_pending_contingent))
    st.query_params.pop("contingent", None)
    st.rerun()

_hood_label = st.query_params.get("hood")
if _hood_label:
    show_neighbourhood_dialog(str(_hood_label))

theme_css.hero(
    "Property comparison",
    "All your properties, ranked and compared.",
)

all_regions = list_regions()

try:
    raw = cached_load_properties(
        tuple(all_regions),
        _sheets_cache_generation(),
        RULES_VERSION,
        FLOOD_GATE_VERSION,
    )
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

raw = add_derived_columns(raw)


def _clear_compare_property_cache() -> None:
    cached_load_properties.clear()


_note_id = st.query_params.get("note")
if _note_id:
    _note_match = raw[raw["Property ID"].astype(str) == str(_note_id)]
    if not _note_match.empty:
        show_property_note_dialog(_note_match.iloc[0], on_saved=_clear_compare_property_cache)

_judgment_id = st.query_params.get("judgment")
if _judgment_id:
    _judgment_match = raw[raw["Property ID"].astype(str) == str(_judgment_id)]
    if not _judgment_match.empty:
        show_judgment_dialog(_judgment_match.iloc[0], on_saved=_clear_compare_property_cache)

region_tab_labels = [*all_regions, ALL_PROPERTIES_TAB]
_region_counts = raw.groupby("Region", sort=False).size().to_dict()

def _region_segment_label(name: str) -> str:
    if name == ALL_PROPERTIES_TAB:
        return f"All properties ({len(raw)})"
    return f"{name} ({_region_counts.get(name, 0)})"


if st.session_state.get("compare_active_region") not in region_tab_labels:
    st.session_state["compare_active_region"] = ALL_PROPERTIES_TAB

active_region = st.segmented_control(
    "Market",
    options=region_tab_labels,
    format_func=_region_segment_label,
    key="compare_active_region",
    label_visibility="collapsed",
)

if active_region == ALL_PROPERTIES_TAB:
    scope = raw
else:
    scope = raw[raw["Region"] == active_region].copy()
    if scope.empty:
        st.info(
            f"No rows on the **{active_region}** Google Sheet tab yet (or the list is stale). "
            "Re-run **Analyze** with a Columbus address, confirm **Save to Google Sheets** is on, "
            "then use **Refresh from Sheets** in the sidebar.",
            icon=":material/info:",
        )

with st.sidebar:
    theme_css.section("Filters", "apartment", "violet")
    st.caption(f"Viewing: **{active_region}**")

    prices = scope["Price"].dropna()
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

    hide_rejected = st.checkbox(
        "Hide rejected listings",
        value=False,
        key="compare_hide_rejected",
        help="Hides rows where your final judgment is Reject.",
    )

    st.space("small")
    if st.button("Reset filters", icon=":material/restart_alt:", width="stretch"):
        st.rerun()
    st.link_button(
        "Open Google Sheets", sheet_url(),
        icon=":material/open_in_new:", width="stretch",
    )
    if st.button("Refresh from Sheets", icon=":material/sync:", width="stretch"):
        st.session_state["sheets_cache_generation"] = (
            st.session_state.get("sheets_cache_generation", 0) + 1
        )
        cached_load_properties.clear()
        st.rerun()

filtered = apply_filters(
    scope,
    regions=[],
    recommendations=[],
    price_range=(price_min, price_max),
    min_overall=min_overall,
    max_commute=max_commute,
    min_beds=min_beds,
    hide_rejected=hide_rejected,
)

active_chips: list[str] = []
if min_overall > 0:
    active_chips.append(f"Match ≥ {min_overall:g}")
if max_commute is not None:
    active_chips.append(f"≤ {int(max_commute)} min")
if min_beds > 0:
    active_chips.append(f"{min_beds}+ beds")
if active_chips:
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
        render_notes_tab(filtered, scope)
