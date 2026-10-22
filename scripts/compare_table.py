"""Compare / visit property tables (shared HTML grid)."""

from __future__ import annotations

import html
import re
import urllib.parse
from collections.abc import Callable
from typing import Any

import pandas as pd

import theme_css
from photos import ensure_thumbnail, readable_property_name
from neighbourhood_tiers import neighbourhood_search_tier
from sheets_data import JUDGMENT_REJECT, JUDGMENT_VISIT, final_judgment_label, judgment_reason_text
from ui_helpers import format_currency, property_title_html

COMPARE_TABLE_HEADERS: list[tuple[str, str]] = [
    ("Property", "property"),
    ("Agent", "agent"),
    ("Neighbourhood", "location"),
    ("Price", "price"),
    ("Days on Zillow", "days_on_zillow"),
    ("House", "house_size"),
    ("Lot", "lot_size"),
    ("HOA / mo", "hoa"),
    ("Units", "units"),
    ("Est. gross rent", "gross_rent"),
    ("Annual tax", "annual_tax"),
    ("Est. net yield", "net_yield"),
    ("Garage / trailer", "trailer"),
    ("Flood risk", "flood"),
    ("Current transit", "transit_now"),
    ("Future transit", "transit_future"),
    ("Area appr.", "appreciation"),
    ("Area rental", "rental"),
    ("Match", "overall"),
    ("Your /10", "my_note"),
    ("Judgment", "judgment"),
    ("Verdict", "verdict"),
]

VISIT_TABLE_HEADERS: list[tuple[str, str]] = [
    ("Visit", "_visit"),
    ("Property", "property"),
    ("Agent", "agent"),
    ("Contact", "_contact"),
    *COMPARE_TABLE_HEADERS[3:],
]

_VERDICT_ORDER = {
    "Buy": 0,
    "Strong candidate": 1,
    "Investigate": 2,
    "Pass": 3,
    "Worth visiting": 1,
    "Save": 2,
    "Reject": 3,
}


def num(value: object, fmt: str = "{:,.0f}", fallback: str = "—") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    try:
        return fmt.format(float(value))
    except (TypeError, ValueError):
        return fallback


def _fraction_10(series: pd.Series) -> pd.Series:
    extracted = series.astype(str).str.extract(r"([\d.]+)\s*/\s*10", expand=False)
    return pd.to_numeric(extracted, errors="coerce")


def _potential_sort_series(
    df: pd.DataFrame,
    *,
    label_column: str,
    score_column: str,
) -> pd.Series:
    labels = df.get(label_column, pd.Series("", index=df.index))
    from_label = _fraction_10(labels)
    scores = pd.to_numeric(
        df.get(score_column, pd.Series(dtype=float, index=df.index)),
        errors="coerce",
    )
    return from_label.where(from_label.notna(), scores)


def _flood_rank(series: pd.Series) -> pd.Series:
    def rank(cell: object) -> int:
        text = str(cell or "")
        if "🔴" in text or text.startswith("High"):
            return 3
        if "🟡" in text or text.startswith("Moderate"):
            return 2
        if "🟢" in text or text.startswith("Low"):
            return 1
        return 0

    return series.map(rank)


def neighbourhood_label(row: pd.Series) -> str:
    hood = str(row.get("Neighbourhood display") or "").strip()
    if hood and hood not in ("—", "nan", "None"):
        return hood
    city = str(row.get("City") or "").strip()
    state = str(row.get("State") or "").strip()
    return f"{city}, {state}".strip(" ,") or "—"


def _neighbourhood_name_sort_series(df: pd.DataFrame) -> pd.Series:
    if "Neighbourhood display" in df.columns:
        return df["Neighbourhood display"].fillna("").astype(str).str.lower()
    return (
        df.get("City", pd.Series("", index=df.index)).fillna("").astype(str)
        + ", "
        + df.get("State", pd.Series("", index=df.index)).fillna("").astype(str)
    ).str.lower()


def _neighbourhood_tier_sort_series(df: pd.DataFrame) -> pd.Series:
    if "Neighbourhood tier" in df.columns:
        tiers = pd.to_numeric(df["Neighbourhood tier"], errors="coerce")
    else:
        tiers = df.get("Neighbourhood display", pd.Series("", index=df.index)).map(
            neighbourhood_search_tier
        )
    return tiers.fillna(99)


def _commute_sort_series(df: pd.DataFrame) -> pd.Series:
    if "Commute (min)" in df.columns:
        return pd.to_numeric(df["Commute (min)"], errors="coerce")
    walk = df.get("Walk to Station", pd.Series("", index=df.index)).astype(str)
    mins = walk.str.extract(r"(\d+)", expand=False)
    return pd.to_numeric(mins, errors="coerce")


def sort_compare_dataframe(
    df: pd.DataFrame,
    sort_key: str,
    *,
    ascending: bool,
) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    key = sort_key.lower()

    if key == "property":
        series = out["Property ID"].astype(str).str.lower()
        return out.assign(_sort=series).sort_values("_sort", ascending=ascending, na_position="last").drop(
            columns="_sort"
        )
    if key == "location":
        tier_series = _neighbourhood_tier_sort_series(out)
        name_series = _neighbourhood_name_sort_series(out)
        return out.assign(_tier=tier_series, _name=name_series).sort_values(
            ["_tier", "_name"],
            ascending=[ascending, True],
            na_position="last",
        ).drop(columns=["_tier", "_name"])
    if key == "price":
        return out.sort_values("Price", ascending=ascending, na_position="last")
    if key == "days_on_zillow" and "Days on Zillow" in out.columns:
        return out.sort_values("Days on Zillow", ascending=ascending, na_position="last")
    if key == "house_size" and "House Size" in out.columns:
        return out.sort_values("House Size", ascending=ascending, na_position="last")
    if key == "lot_size" and "Land Size" in out.columns:
        return out.sort_values("Land Size", ascending=ascending, na_position="last")
    if key == "hoa":
        return out.sort_values("HOA", ascending=ascending, na_position="last")
    if key == "units":
        col = "Legal Units" if "Legal Units" in out.columns else "Units"
        if col in out.columns:
            return out.sort_values(col, ascending=ascending, na_position="last")
    if key == "gross_rent" and "Estimated Rent" in out.columns:
        return out.sort_values("Estimated Rent", ascending=ascending, na_position="last")
    if key == "annual_tax" and "Taxes" in out.columns:
        return out.sort_values("Taxes", ascending=ascending, na_position="last")
    if key == "net_yield" and "Est. net yield %" in out.columns:
        return out.sort_values("Est. net yield %", ascending=ascending, na_position="last")
    if key == "trailer" and "Trailer" in out.columns:
        return out.sort_values(
            "Trailer",
            ascending=ascending,
            na_position="last",
            key=lambda s: s.astype(str).str.lower(),
        )
    if key == "flood":
        return out.assign(_sort=_flood_rank(out.get("Flood", pd.Series("", index=df.index)))).sort_values(
            "_sort", ascending=ascending, na_position="last"
        ).drop(columns="_sort")
    if key == "transit_now":
        return out.assign(_sort=_commute_sort_series(out)).sort_values(
            "_sort", ascending=ascending, na_position="last"
        ).drop(columns="_sort")
    if key == "transit_future" and "Transit future" in out.columns:
        return out.sort_values(
            "Transit future",
            ascending=ascending,
            na_position="last",
            key=lambda s: s.astype(str).str.lower(),
        )
    if key == "appreciation":
        series = _potential_sort_series(
            out, label_column="Appreciation label", score_column="Appreciation"
        )
        return out.assign(_sort=series).sort_values("_sort", ascending=ascending, na_position="last").drop(
            columns="_sort"
        )
    if key == "rental":
        series = _potential_sort_series(
            out, label_column="Rental potential", score_column="Rental"
        )
        return out.assign(_sort=series).sort_values("_sort", ascending=ascending, na_position="last").drop(
            columns="_sort"
        )
    if key == "my_note" and "Wow Factor" in out.columns:
        return out.sort_values("Wow Factor", ascending=ascending, na_position="last")
    if key == "judgment" and "Final Decision" in out.columns:
        order = {JUDGMENT_VISIT: 0, JUDGMENT_REJECT: 1, "": 2}
        series = out["Final Decision"].map(
            lambda v: order.get(str(v or "").strip(), 3)
        )
        return out.assign(_sort=series).sort_values("_sort", ascending=ascending, na_position="last").drop(
            columns="_sort"
        )
    if key == "verdict":
        verdicts = out.get("Verdict", pd.Series("", index=out.index)).astype(str).str.strip()
        order = verdicts.map(_VERDICT_ORDER).fillna(99)
        return out.assign(_sort=order).sort_values(
            ["_sort", "Overall"],
            ascending=[ascending, False],
            na_position="last",
        ).drop(columns="_sort")
    if key == "overall" and "Overall" in out.columns:
        return out.sort_values("Overall", ascending=ascending, na_position="last")
    return out.sort_values("Overall", ascending=False, na_position="last")


def default_sort_ascending(sort_key: str) -> bool:
    return sort_key in {
        "property",
        "location",
        "trailer",
        "transit_now",
        "transit_future",
        "verdict",
        "my_note",
        "judgment",
    }


def _clipped_cell(text: str, *, lines: int = 1) -> str:
    safe = html.escape(str(text or "—").strip() or "—")
    title = html.escape(str(text or "").strip())
    title_attr = f' title="{title}"' if title else ""
    if lines > 1:
        return f'<div class="pc-cell-clamp"{title_attr}>{safe}</div>'
    return f'<div class="pc-cell-clip"{title_attr}>{safe}</div>'


def _days_on_zillow_label(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        days = int(float(value))
    except (TypeError, ValueError):
        return "—"
    if days < 0:
        return "—"
    return str(days)


def _sqft_label(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        sqft = float(value)
    except (TypeError, ValueError):
        return "—"
    if sqft <= 0:
        return "—"
    return f"{int(round(sqft)):,} sf"


def _hood_tier(row: pd.Series) -> int | None:
    tier = row.get("Neighbourhood tier")
    if tier is not None and not (isinstance(tier, float) and pd.isna(tier)):
        try:
            return int(tier)
        except (TypeError, ValueError):
            pass
    return neighbourhood_search_tier(neighbourhood_label(row))


def hood_badge_html(row: pd.Series, *, href: str | None = None) -> str:
    badge = theme_css.hood_tier_badge_html(neighbourhood_label(row), _hood_tier(row))
    if not href:
        return badge
    return f'<a class="pc-hood-link" href="{html.escape(href)}">{badge}</a>'


def annual_tax_label(row: pd.Series) -> str:
    tax = row.get("Taxes")
    if tax is None or (isinstance(tax, float) and pd.isna(tax)):
        return "—"
    try:
        amount = float(tax)
    except (TypeError, ValueError):
        return "—"
    if amount <= 0:
        return "—"
    return format_currency(amount)


def group_by_neighbourhood(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """Neighbourhood sections, best match score first within each."""
    if df.empty:
        return []
    out = df.copy()
    out["_hood"] = out.apply(neighbourhood_label, axis=1)
    groups: list[tuple[str, pd.DataFrame]] = []
    for hood, chunk in out.groupby("_hood", sort=False):
        ranked = sort_compare_dataframe(chunk.drop(columns="_hood"), "overall", ascending=False)
        groups.append((str(hood), ranked))

    def group_rank(item: tuple[str, pd.DataFrame]) -> tuple[float, int, str]:
        _, frame = item
        best = float(frame["Overall"].max()) if frame["Overall"].notna().any() else 0.0
        tier = int(_neighbourhood_tier_sort_series(frame).min()) if len(frame) else 99
        return (-best, tier, item[0].lower())

    groups.sort(key=group_rank)
    return groups


def _sort_header_link(
    label: str,
    sort_key: str,
    *,
    active_key: str,
    active_asc: bool,
    href_builder: Callable[..., str],
    sticky: bool = False,
    sticky_end: bool = False,
    non_sortable: bool = False,
) -> str:
    if non_sortable:
        cls = "pc-sort-link pc-sort-static"
        if sticky:
            cls += " pc-sticky-prop pc-sticky-head"
        return f'<span class="{cls}">{html.escape(label)}</span>'
    is_active = active_key == sort_key
    arrow = (" ▲" if active_asc else " ▼") if is_active else ""
    if is_active:
        next_asc = not active_asc
    else:
        next_asc = default_sort_ascending(sort_key)
    href = href_builder(compare_sort=sort_key, compare_dir="asc" if next_asc else "desc")
    cls = "pc-sort-link"
    if is_active:
        cls += " pc-sort-active"
    if sticky:
        cls += " pc-sticky-prop pc-sticky-head"
    if sticky_end:
        cls += " pc-verdict-col pc-verdict-head"
    inner = f"{html.escape(label)}{arrow}"
    return f'<a class="{cls}" href="{html.escape(href)}">{inner}</a>'


def _status_toggle(pid: str, on: bool, href: str, *, on_label: str, off_label: str, title: str, extra_class: str = "") -> str:
    state = "pc-visit-on" if on else "pc-visit-off"
    word = on_label if on else off_label
    mark = "✓" if on else ""
    cls = f"pc-contacted-toggle {state} {extra_class}".strip()
    return (
        f"<a class='{cls}' href='{html.escape(href)}' title='{html.escape(title)}'>"
        f"<span class='pc-visit-box'>{mark}</span>{html.escape(word)}</a>"
    )


def _visit_checkbox_cell(pid: str, picked: bool, toggle_href: Callable[[str], str]) -> str:
    state = "pc-visit-on" if picked else "pc-visit-off"
    mark = "✓" if picked else ""
    href = html.escape(toggle_href(pid))
    return (
        f'<a class="pc-visit-toggle {state}" href="{href}" title="Include on visit day">'
        f'<span class="pc-visit-box">{mark}</span></a>'
    )


def _note_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _personal_score_cell(
    pid: str,
    wow: object,
    notes: object,
    note_href: Callable[[str], str],
) -> str:
    from scoring import wow_factor_value
    from sheets_data import personal_note_text

    score = wow_factor_value(wow)
    note = personal_note_text(notes)
    display = f"{score:g}/10" if score is not None else "Set /10"
    empty = " pc-note-empty" if score is None else ""
    href = html.escape(note_href(pid))
    bits = []
    if score is not None:
        bits.append(f"Your score {score:g}/10 (20% of match)")
    if note:
        bits.append(note)
    title = html.escape(" · ".join(bits) if bits else "Set your score out of 10")
    return (
        f'<a class="pc-note-link{empty}" href="{href}" title="{title}">'
        f"{html.escape(display)}</a>"
    )


def _judgment_cell(
    pid: str,
    decision: object,
    reason: object,
    judgment_href: Callable[[str], str],
) -> str:
    label = final_judgment_label(decision)
    reason_text = judgment_reason_text(reason)
    if label == JUDGMENT_VISIT:
        display = "Visit"
        cls = "pc-judgment-visit"
    elif label == JUDGMENT_REJECT:
        display = "Reject"
        cls = "pc-judgment-reject"
    else:
        display = "Set"
        cls = "pc-judgment-empty"
    title = html.escape(reason_text if reason_text else "Set visit or reject")
    href = html.escape(judgment_href(pid))
    return (
        f'<a class="pc-judgment-link {cls}" href="{href}" title="{title}">'
        f"{html.escape(display)}</a>"
    )


def _agent_cell(name: object, phone: object) -> str:
    name_s = str(name or "").strip()
    phone_s = str(phone or "").strip()
    if not name_s and not phone_s:
        return "<div class='pc-cell pc-contact-empty'>—</div>"
    bits: list[str] = []
    if name_s:
        bits.append(f"<div class='pc-cell'>{html.escape(name_s)}</div>")
    if phone_s:
        tel = re.sub(r"[^\d+]", "", phone_s) or phone_s
        bits.append(
            f"<div class='pc-prop-sub'><a href='tel:{html.escape(tel)}'>"
            f"{html.escape(phone_s)}</a></div>"
        )
    return "".join(bits)


def _contact_cell(pid: str, phone: str, contact_href: Callable[[str], str]) -> str:
    label = phone.strip() if phone.strip() else "Add number"
    href = html.escape(contact_href(pid))
    tel = html.escape(phone.strip())
    if tel:
        return (
            f'<a class="pc-contact-link" href="{href}">{html.escape(label)}</a>'
            f'<div class="pc-prop-sub"><a href="tel:{tel}">Call</a></div>'
        )
    return f'<a class="pc-contact-link pc-contact-empty" href="{href}">{html.escape(label)}</a>'


def build_row_cells(
    row: pd.Series,
    *,
    headers: list[tuple[str, str]],
    nav_href: Callable[..., str],
    visit_mode: bool = False,
    picked_ids: set[str] | None = None,
    toggle_href: Callable[[str], str] | None = None,
    contact_href: Callable[[str], str] | None = None,
    contact_phones: dict[str, str] | None = None,
    contacted_ids: set[str] | None = None,
    contacted_href: Callable[[str], str] | None = None,
    contingent_ids: set[str] | None = None,
    contingent_href: Callable[[str], str] | None = None,
    note_href: Callable[[str], str] | None = None,
    judgment_href: Callable[[str], str] | None = None,
) -> list[str]:
    pid = str(row["Property ID"])
    thumb = ensure_thumbnail(pid)
    name_html = property_title_html(readable_property_name(pid), row.get("Link"))
    verdict = str(row.get("Verdict") or "—")
    match = row.get("Match /100")
    match_label = f"{float(match):.0f}" if pd.notna(match) else "—"
    score = float(row["Overall"]) if pd.notna(row.get("Overall")) else 0.0
    score_pct = int(min(max(score / 10.0, 0.0), 1.0) * 100)
    vclass = theme_css.verdict_class(verdict)
    flood = str(row.get("Flood") or "—")
    thumb_inner = (
        f'<img class="pc-thumb" src="/app/static/property_thumbs/{html.escape(thumb.name)}" alt="" />'
        if thumb is not None
        else '<div class="pc-thumb pc-thumb-empty"></div>'
    )
    status_bits: list[str] = []
    if contacted_ids is not None:
        status_bits.append(
            _status_toggle(
                pid,
                pid in contacted_ids,
                (contacted_href or (lambda _p: "?"))(pid),
                on_label="Contacted",
                off_label="Not contacted",
                title="Mark as contacted",
            )
        )
    if contingent_ids is not None:
        status_bits.append(
            _status_toggle(
                pid,
                pid in contingent_ids,
                (contingent_href or (lambda _p: "?"))(pid),
                on_label="Contingent",
                off_label="Not contingent",
                title="Mark as contingent",
                extra_class="pc-contingent-toggle",
            )
        )
    hood_href = nav_href(hood=neighbourhood_label(row))
    hood_html = hood_badge_html(row, href=hood_href)
    sticky_prop = (
        f'<div class="pc-sticky-prop">{thumb_inner}'
        f'<div class="pc-sticky-prop-text">{name_html}'
        f"<div class='pc-prop-sub pc-cell-hood-clip'>{hood_html}</div>"
        f"<div class='pc-status-toggles'>{''.join(status_bits)}</div>"
        f"</div></div>"
    )
    net = row.get("Est. net yield %")
    net_label = f"{float(net):.1f}%" if pd.notna(net) else "—"
    tax_label = annual_tax_label(row)
    hoa_label = format_currency(row.get("HOA"))
    if hoa_label in ("$0", "—"):
        hoa_label = "—"

    data_cells: dict[str, str] = {
        "property": sticky_prop,
        "agent": _agent_cell(row.get("Listing agent"), row.get("Agent phone")),
        "location": f"<div class='pc-cell pc-cell-hood-clip'>{hood_html}</div>",
        "price": f"<div class='pc-cell-strong'>${html.escape(num(row.get('Price')))}</div>",
        "days_on_zillow": f"<div class='pc-cell'>{_days_on_zillow_label(row.get('Days on Zillow'))}</div>",
        "house_size": f"<div class='pc-cell'>{_clipped_cell(_sqft_label(row.get('House Size')))}</div>",
        "lot_size": f"<div class='pc-cell'>{_clipped_cell(_sqft_label(row.get('Land Size')))}</div>",
        "hoa": f"<div class='pc-cell'>{html.escape(hoa_label)}</div>",
        "units": f"<div class='pc-cell'>{_clipped_cell(str(row.get('Units') or '—'))}</div>",
        "gross_rent": f"<div class='pc-cell'>{_clipped_cell(str(row.get('Gross rent label') or '—'))}</div>",
        "annual_tax": f"<div class='pc-cell'>{html.escape(tax_label)}</div>",
        "net_yield": f"<div class='pc-cell-strong'>{_clipped_cell(net_label)}</div>",
        "trailer": f"<div class='pc-cell'>{_clipped_cell(str(row.get('Trailer') or '—'))}</div>",
        "flood": f"<div class='pc-cell'>{theme_css.flood_risk_badge_html(flood)}</div>",
        "transit_now": f"<div class='pc-cell'>{_clipped_cell(str(row.get('Transit now') or '—'))}</div>",
        "transit_future": f"<div class='pc-cell'>{_clipped_cell(str(row.get('Transit future') or '—'))}</div>",
        "appreciation": f"<div class='pc-cell'>{_clipped_cell(str(row.get('Appreciation label') or '—'))}</div>",
        "rental": f"<div class='pc-cell'>{_clipped_cell(str(row.get('Rental potential') or '—'))}</div>",
        "my_note": _personal_score_cell(
            pid,
            row.get("Wow Factor"),
            row.get("Notes"),
            note_href or (lambda p: nav_href(note=p)),
        ),
        "judgment": _judgment_cell(
            pid,
            row.get("Final Decision"),
            row.get("Judgment reason"),
            judgment_href or (lambda p: nav_href(judgment=p)),
        ),
        "overall": (
            f"<a class='pc-match-link' href='{html.escape(nav_href(scores=pid))}' title='View match breakdown'>"
            "<div class='pc-match'>"
            f"<div class='pc-match-val'>{html.escape(match_label)}</div>"
            f"<div class='pc-match-bar'><div class='pc-match-fill' style='width:{score_pct}%'></div></div>"
            "</div></a>"
        ),
        "verdict": (
            f"<a class='pc-verdict-link' href='{html.escape(nav_href(verdict=pid))}' title='Why this verdict?'>"
            f"<div class='pc-verdict-col'><span class='pc-verdict {vclass}'>"
            f"{html.escape(verdict)}</span>"
            f"<div class='pc-prop-sub'>Why?</div></div></a>"
        ),
        "_visit": _visit_checkbox_cell(
            pid,
            pid in (picked_ids or set()),
            toggle_href or (lambda _p: "?"),
        ),
        "_contact": _contact_cell(
            pid,
            (contact_phones or {}).get(pid, ""),
            contact_href or (lambda _p: "?"),
        ),
    }

    return [data_cells[key] for _label, key in headers]


def render_table_html(
    ranked: pd.DataFrame,
    *,
    headers: list[tuple[str, str]],
    sort_key: str,
    sort_asc: bool,
    href_builder: Callable[..., str],
    wrap_class: str = "pc-compare-wrap",
    visit_mode: bool = False,
    picked_ids: set[str] | None = None,
    toggle_href: Callable[[str], str] | None = None,
    contact_href: Callable[[str], str] | None = None,
    contact_phones: dict[str, str] | None = None,
    contacted_ids: set[str] | None = None,
    contacted_href: Callable[[str], str] | None = None,
    contingent_ids: set[str] | None = None,
    contingent_href: Callable[[str], str] | None = None,
    note_href: Callable[[str], str] | None = None,
    judgment_href: Callable[[str], str] | None = None,
) -> str:
    n_cols = len(headers)
    head_cells = [
        _sort_header_link(
            label,
            key,
            active_key=sort_key,
            active_asc=sort_asc,
            href_builder=href_builder,
            sticky=(idx == (1 if visit_mode else 0)),
            sticky_end=(idx == n_cols - 1),
            non_sortable=key in {"_visit", "_contact"},
        )
        for idx, (label, key) in enumerate(headers)
    ]
    bodies: list[str] = []
    for _, row in ranked.iterrows():
        cells = build_row_cells(
            row,
            headers=headers,
            nav_href=href_builder,
            visit_mode=visit_mode,
            picked_ids=picked_ids,
            toggle_href=toggle_href,
            contact_href=contact_href,
            contact_phones=contact_phones,
            contacted_ids=contacted_ids,
            contacted_href=contacted_href,
            contingent_ids=contingent_ids,
            contingent_href=contingent_href,
            note_href=note_href,
            judgment_href=judgment_href,
        )
        if len(cells) != n_cols:
            raise RuntimeError(f"Table column mismatch: {len(cells)} vs {n_cols}")
        bodies.append(f'<div class="pc-compare-row">{"".join(cells)}</div>')
    return (
        f'<div class="{wrap_class}">'
        f'<div class="pc-compare-head">{"".join(head_cells)}</div>'
        + "".join(bodies)
        + "</div>"
    )
