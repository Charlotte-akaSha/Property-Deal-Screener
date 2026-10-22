"""Visit organizer: compare-style tables by neighbourhood, then plan visit days."""

from __future__ import annotations

import sys
import urllib.parse
from datetime import date, time
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import theme_css  # noqa: E402
from compare_table import (  # noqa: E402
    VISIT_TABLE_HEADERS,
    group_by_neighbourhood,
    hood_badge_html,
    render_table_html,
    sort_compare_dataframe,
)
from geocode import address_for, coordinates_for  # noqa: E402
from flood_lookup import FLOOD_GATE_VERSION  # noqa: E402
from neighbourhood_tiers import RULES_VERSION  # noqa: E402
from photos import readable_property_name  # noqa: E402
from sheets_data import load_properties  # noqa: E402
from ui_helpers import (  # noqa: E402
    normalize_listing_url,
    show_judgment_dialog,
    show_neighbourhood_dialog,
    show_property_note_dialog,
)
from visit_contacts import get_contact, set_contact, whatsapp_href  # noqa: E402
from visit_planner import (  # noqa: E402
    VisitDay,
    VisitStop,
    default_message,
    group_into_days,
    schedule_day,
    stops_from_rows,
)
from write_to_sheets import list_regions  # noqa: E402

PICK_KEY = "visit_pick_ids"


@st.cache_data(ttl="10m", show_spinner="Loading properties…")
def _load(regions: tuple[str, ...], _hood_rules: int, _flood_gate: int) -> pd.DataFrame:
    del _hood_rules, _flood_gate
    return load_properties(list(regions))


def _picked() -> list[str]:
    raw = st.session_state.get(PICK_KEY) or []
    return [str(x) for x in raw]


def _set_picked(ids: list[str]) -> None:
    seen: set[str] = set()
    out: list[str] = []
    for pid in ids:
        if pid and pid not in seen:
            seen.add(pid)
            out.append(pid)
    st.session_state[PICK_KEY] = out


def _sync_visit_sort() -> tuple[str, bool]:
    qp_sort = st.query_params.get("compare_sort")
    qp_dir = st.query_params.get("compare_dir")
    if qp_sort:
        st.session_state["visit_sort"] = str(qp_sort)
        st.session_state["visit_sort_asc"] = str(qp_dir or "desc").lower() == "asc"
    sort_key = str(st.session_state.get("visit_sort", "overall"))
    ascending = bool(st.session_state.get("visit_sort_asc", False))
    return sort_key, ascending


def _visits_nav_href(**extra: str) -> str:
    sort_key, sort_asc = _sync_visit_sort()
    params: dict[str, str] = {
        "compare_sort": sort_key,
        "compare_dir": "asc" if sort_asc else "desc",
    }
    for key, value in extra.items():
        if value:
            params[key] = value
    return "?" + urllib.parse.urlencode(params)


def _row_nav_href(**extra: str) -> str:
    """Match / verdict open on Compare; selection stays on Visits."""
    if extra.get("scores") or extra.get("verdict"):
        sort_key, sort_asc = _sync_visit_sort()
        params: dict[str, str] = {
            "compare_sort": sort_key,
            "compare_dir": "asc" if sort_asc else "desc",
            **{k: v for k, v in extra.items() if v},
        }
        return "/compare?" + urllib.parse.urlencode(params)
    return _visits_nav_href(**extra)


def _contact_phones(property_ids: list[str]) -> dict[str, str]:
    return {pid: (get_contact(pid).get("phone") or "") for pid in property_ids}


def render_sidebar_prefs() -> tuple[time, time, int, date]:
    st.subheader("Visit window")
    start = st.time_input("From", value=time(9, 30), key="visit_start")
    end = st.time_input("Until", value=time(17, 0), key="visit_end")
    minutes = st.slider("Minutes at each property", min_value=20, max_value=60, value=35, step=5)
    visit_date = st.date_input("First day", value=date.today())
    st.caption(
        "After you pick listings, we group them into days (5–8 nearby stops) and suggest times. "
        "Travel is estimated from map pins, not live traffic."
    )
    return start, end, int(minutes), visit_date


def render_neighbourhood_tables(df: pd.DataFrame, picked: set[str]) -> None:
    sort_key, sort_asc = _sync_visit_sort()
    groups = group_by_neighbourhood(df)
    if not groups:
        st.info("No properties to show.", icon=":material/inventory_2:")
        return

    all_ids = [str(r["Property ID"]) for _, chunk in groups for _, r in chunk.iterrows()]
    phones = _contact_phones(all_ids)

    st.caption(
        f"{len(picked)} selected for visits · neighbourhoods ordered by best match score. "
        "Within each area, strongest listings are first. Click **Visit** to include a row; "
        "**Contact** to add the listing phone (saved on this computer)."
    )

    for hood, chunk in groups:
        ranked = sort_compare_dataframe(chunk, sort_key, ascending=sort_asc).reset_index(drop=True)
        sample = ranked.iloc[0]
        with theme_css.card(f"visit_hood_{hood[:40]}"):
            theme_css.chip_row(
                hood_badge_html(sample, href=_visits_nav_href(hood=hood)),
                f'<span class="pc-chip">{len(ranked)} listings</span>',
                f'<span class="pc-chip">Best match {sample.get("Overall", 0):.1f}/10</span>'
                if pd.notna(sample.get("Overall"))
                else '<span class="pc-chip">—</span>',
            )
            st.html(
                render_table_html(
                    ranked,
                    headers=VISIT_TABLE_HEADERS,
                    sort_key=sort_key,
                    sort_asc=sort_asc,
                    href_builder=_row_nav_href,
                    wrap_class="pc-compare-wrap pc-visit-grid",
                    visit_mode=True,
                    picked_ids=picked,
                    toggle_href=lambda pid: _visits_nav_href(visit_toggle=pid),
                    contact_href=lambda pid: _visits_nav_href(contact=pid),
                    contact_phones=phones,
                    note_href=lambda pid: _visits_nav_href(note=pid),
                    judgment_href=lambda pid: _visits_nav_href(judgment=pid),
                )
            )


def render_stop(stop: VisitStop, *, day_index: int, stop_index: int) -> None:
    travel = f" · ~{stop.travel_from_prev_min} min from previous" if stop.travel_from_prev_min else ""
    window = ""
    if stop.arrive and stop.depart:
        window = f"{stop.arrive.strftime('%-I:%M %p')} – {stop.depart.strftime('%-I:%M %p')}"
    st.markdown(f"**{stop_index}. {stop.label}**")
    bits = [b for b in (window, stop.neighbourhood or None, stop.address or None) if b]
    st.caption(" · ".join(bits) + travel)
    if stop.phone:
        st.caption(f"Contact: {stop.phone}")

    link = normalize_listing_url(stop.link)
    c1, c2 = st.columns([1.2, 1])
    with c1:
        if link:
            st.link_button("Listing", link, icon=":material/open_in_new:")
    with c2:
        msg_key = f"wa_msg_{stop.property_id}"
        when = stop.arrive.strftime("%A %-I:%M %p") if stop.arrive else ""
        if msg_key not in st.session_state:
            st.session_state[msg_key] = default_message(stop, when)
        st.text_area("WhatsApp message", key=msg_key, height=100)
        href = whatsapp_href(stop.phone, str(st.session_state.get(msg_key, "")))
        if href:
            st.link_button("Open WhatsApp", href, icon=":material/chat:", type="primary")
        elif stop.phone:
            st.caption("Phone looks too short for WhatsApp.")
        else:
            st.caption("Add a contact number in the neighbourhood table above.")


def render_day(day: VisitDay) -> None:
    count = len(day.stops)
    tone = "mint" if 5 <= count <= 8 else "amber"
    theme_css.section(f"Day {day.day_index} — {day.title}", "calendar_month", tone)
    st.caption(f"{count} stops")
    for i, stop in enumerate(day.stops, start=1):
        with st.container(border=True):
            render_stop(stop, day_index=day.day_index, stop_index=i)


def render_itinerary(
    df: pd.DataFrame,
    ids: list[str],
    start: time,
    end: time,
    minutes: int,
    first_day: date,
) -> None:
    subset = df[df["Property ID"].isin(ids)].copy()
    if subset.empty:
        st.info("Those selections are not on the Sheet.", icon=":material/info:")
        return
    order = {pid: i for i, pid in enumerate(ids)}
    subset["_ord"] = subset["Property ID"].map(lambda p: order.get(str(p), 999))
    subset = subset.sort_values("_ord")

    coords = coordinates_for(list(subset["Property ID"].astype(str)))
    missing = [pid for pid in subset["Property ID"].astype(str) if pid not in coords]
    if missing:
        st.warning(
            f"{len(missing)} listing(s) have no map pin yet: "
            + ", ".join(readable_property_name(p) for p in missing[:6]),
            icon=":material/location_off:",
        )

    stops = stops_from_rows(
        subset,
        coords,
        {pid: get_contact(pid) for pid in subset["Property ID"].astype(str)},
        label_for=readable_property_name,
        address_for=address_for,
    )
    days = group_into_days(stops)
    warnings: list[str] = []
    from datetime import datetime, timedelta

    for offset, day in enumerate(days):
        on = datetime.combine(first_day + timedelta(days=offset), time.min)
        _, day_warnings = schedule_day(
            day,
            start_hour=start.hour,
            start_minute=start.minute,
            end_hour=end.hour,
            end_minute=end.minute,
            minutes_per_stop=minutes,
            on_date=on,
        )
        warnings.extend(day_warnings)

    for msg in warnings:
        st.warning(msg, icon=":material/schedule:")
    for day in days:
        render_day(day)


def _handle_query_actions() -> None:
    toggle = st.query_params.get("visit_toggle")
    if toggle:
        pid = str(toggle)
        current = set(_picked())
        if pid in current:
            current.remove(pid)
        else:
            current.add(pid)
        _set_picked(list(current))
        st.query_params.pop("visit_toggle", None)
        st.rerun()

    contact_id = st.query_params.get("contact")
    if contact_id:
        pid = str(contact_id)
        existing = get_contact(pid)

        @st.dialog(f"Contact — {readable_property_name(pid)}", width="small")
        def edit_contact() -> None:
            st.caption("Saved locally on this computer, not in Google Sheets.")
            phone = st.text_input("Listing phone", value=existing.get("phone", ""))
            agent = st.text_input("Agent name (optional)", value=existing.get("agent_name", ""))
            if st.button("Save", type="primary"):
                set_contact(pid, phone=phone, agent_name=agent)
                st.query_params.pop("contact", None)
                st.rerun()
            if st.button("Cancel"):
                st.query_params.pop("contact", None)
                st.rerun()

        edit_contact()


# --- Page ---

theme_css.hero(
    "Visit organizer",
    "Compare listings by neighbourhood, pick who to see, then build a sensible day route.",
)

_handle_query_actions()

_hood_label = st.query_params.get("hood")
if _hood_label:
    show_neighbourhood_dialog(str(_hood_label))

with st.sidebar:
    start_t, end_t, mins, first = render_sidebar_prefs()
    n_picked = len(_picked())
    st.metric("Selected for visits", n_picked)
    if st.button("Clear selection", icon=":material/close:"):
        _set_picked([])
        st.rerun()

regions = list_regions()
try:
    raw = _load(tuple(regions), RULES_VERSION, FLOOD_GATE_VERSION)
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not load your Google Sheet: {exc}", icon=":material/cloud_off:")
    st.stop()

if raw.empty:
    st.info("No properties on the Sheet yet.", icon=":material/inventory_2:")
    st.stop()

_note_id = st.query_params.get("note")
if _note_id:
    _note_match = raw[raw["Property ID"].astype(str) == str(_note_id)]
    if not _note_match.empty:
        show_property_note_dialog(_note_match.iloc[0], on_saved=_load.clear)

_judgment_id = st.query_params.get("judgment")
if _judgment_id:
    _judgment_match = raw[raw["Property ID"].astype(str) == str(_judgment_id)]
    if not _judgment_match.empty:
        show_judgment_dialog(_judgment_match.iloc[0], on_saved=_load.clear)

add_id = st.query_params.get("add")
if add_id and str(add_id) in set(raw["Property ID"].astype(str)):
    _set_picked(_picked() + [str(add_id)])
    st.query_params.pop("add", None)

rec_filter = st.multiselect(
    "Show recommendations",
    options=sorted(raw["Recommendation"].dropna().unique().tolist()),
    default=["Worth visiting", "Save"],
)
shown = raw.copy()
if rec_filter:
    shown = shown[shown["Recommendation"].isin(rec_filter)]

picked_set = set(_picked())

tab_choose, tab_plan = st.tabs(["Choose listings", "Itinerary"])

with tab_choose:
    render_neighbourhood_tables(shown, picked_set)

with tab_plan:
    ids = _picked()
    if not ids:
        st.info("Check **Visit** on at least one listing in the first tab.", icon=":material/checklist:")
    elif start_t >= end_t:
        st.error("End time must be after start time.")
    else:
        if st.button("Suggest days and times", type="primary", icon=":material/route:"):
            st.session_state["visit_plan_ready"] = True
        if st.session_state.get("visit_plan_ready"):
            render_itinerary(raw, ids, start_t, end_t, mins, first)
