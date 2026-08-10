"""Portfolio comparison design system — clean SaaS glass, not neumorphism."""

from __future__ import annotations

import html as _html

import streamlit as st

# Soft pastel accents for KPI icon wells (tint, icon)
ACCENTS = {
    "violet": ("#EFEBFB", "#6D5EF5"),
    "mint": ("#E6F4F1", "#3D9B8F"),
    "blue": ("#E8F0FC", "#5B8DEF"),
    "peach": ("#F8EEE6", "#D4924A"),
    "rose": ("#F7E9EB", "#D4717A"),
    "amber": ("#F6F0E4", "#C9A227"),
}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,500,0,0&display=swap');

:root {
  --pc-bg: #F4F5FB;
  --pc-card: #FFFFFF;
  --pc-text: #1F2433;
  --pc-muted: #8B92A8;
  --pc-line: #E8EBF3;
  --pc-accent: #6D5EF5;
  --pc-radius: 12px;
  --pc-shadow: 0 1px 2px rgba(31,36,51,.04), 0 8px 24px rgba(31,36,51,.06);
}

html, body, [data-testid="stAppViewContainer"], .stMarkdown, .stCaption, label {
  font-family: Inter, system-ui, -apple-system, sans-serif !important;
}

[data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg, #F6F7FC 0%, #F0F2F8 100%);
}
[data-testid="stHeader"] {
  background: transparent;
}
/* Top nav lives in the absolute header bar — main content must clear it. */
[data-testid="stMainBlockContainer"].block-container,
.block-container {
  padding-top: 5.25rem !important;
  padding-bottom: 3rem !important;
  max-width: 1280px;
}

/* ---------- Cards ---------- */
[class*="st-key-nucard"] {
  background: var(--pc-card) !important;
  border: 1px solid var(--pc-line) !important;
  border-radius: 16px !important;
  padding: 20px 22px !important;
  box-shadow: var(--pc-shadow) !important;
  backdrop-filter: none !important;
}
[class*="st-key-nucard_table"] {
  padding: 8px 8px 12px !important;
}
[class*="st-key-nucard_table"] img {
  border-radius: 8px !important;
  object-fit: cover !important;
  width: 64px !important;
  height: 64px !important;
  aspect-ratio: 1 / 1;
  box-shadow: none !important;
}
[data-testid="stForm"] {
  border: none !important;
  background: transparent !important;
  padding: 0 !important;
}

/* ---------- Buttons ---------- */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button,
.stLinkButton > a {
  border: 1px solid var(--pc-line) !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  letter-spacing: 0 !important;
  padding: 0.5rem 1rem !important;
  background: #FFFFFF !important;
  color: #3A4158 !important;
  box-shadow: 0 1px 2px rgba(31,36,51,.05) !important;
  transition: background .15s ease, border-color .15s ease, color .15s ease;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover,
.stLinkButton > a:hover {
  transform: none !important;
  border-color: #D0D5E4 !important;
  color: var(--pc-accent) !important;
  box-shadow: 0 1px 2px rgba(31,36,51,.06) !important;
}
.stButton > button:active,
.stFormSubmitButton > button:active,
.stDownloadButton > button:active {
  transform: none !important;
  box-shadow: none !important;
}
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
  background: linear-gradient(135deg, #6D5EF5 0%, #5B8DEF 100%) !important;
  border: none !important;
  color: #FFFFFF !important;
  box-shadow: 0 4px 14px rgba(109,94,245,.28) !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
  color: #FFFFFF !important;
  filter: brightness(1.04);
}

/* ---------- Tabs: underline style ---------- */
[role="tablist"] {
  gap: 4px !important;
  background: transparent;
  border-bottom: 1px solid var(--pc-line) !important;
  padding: 0 0 0 0;
  margin-bottom: 8px;
}
[data-testid="stTab"] {
  border: none !important;
  border-radius: 0 !important;
  padding: 12px 16px !important;
  background: transparent !important;
  box-shadow: none !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  color: var(--pc-muted) !important;
}
[data-testid="stTab"]:hover {
  transform: none !important;
  color: var(--pc-text) !important;
}
[data-testid="stTab"][aria-selected="true"] {
  background: transparent !important;
  color: var(--pc-accent) !important;
  box-shadow: inset 0 -2px 0 var(--pc-accent) !important;
}
[data-testid="stTab"] [data-testid="stMarkdownContainer"] { color: inherit !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }

/* ---------- Inputs ---------- */
[data-testid="stTextInputRootElement"],
[data-testid="stTextAreaRootElement"],
[data-testid="stNumberInputContainer"],
[data-baseweb="select"] > div {
  border: 1px solid var(--pc-line) !important;
  border-radius: 10px !important;
  background: #FFFFFF !important;
  box-shadow: none !important;
}
[data-testid="stTextInputRootElement"] input,
[data-testid="stNumberInputContainer"] input,
.stTextArea textarea {
  background: transparent !important;
  border: none !important;
}
[data-testid="stFileUploaderDropzone"] {
  border: 1px dashed #D0D5E4 !important;
  border-radius: 12px !important;
  background: #FAFBFE !important;
  box-shadow: none !important;
}

/* ---------- Pills / segmented ---------- */
[data-testid="stPills"] button,
[data-testid="stSegmentedControl"] button {
  border: 1px solid var(--pc-line) !important;
  border-radius: 8px !important;
  background: #FFFFFF !important;
  box-shadow: none !important;
  font-weight: 500 !important;
}
[data-testid="stPills"] button[aria-checked="true"],
[data-testid="stSegmentedControl"] button[aria-checked="true"] {
  background: #EFEBFB !important;
  border-color: #D4CDFF !important;
  color: var(--pc-accent) !important;
  box-shadow: none !important;
}

/* ---------- Data tables ---------- */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
  border-radius: 12px !important;
  overflow: hidden;
  box-shadow: none !important;
  border: 1px solid var(--pc-line) !important;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
  background: #1B1F36 !important;
  border-right: none !important;
  box-shadow: 8px 0 28px rgba(15, 18, 35, 0.18);
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] .stCaption {
  color: #C5CAD9 !important;
}
[data-testid="stSidebar"] .nu-section-title {
  color: #F2F3F8 !important;
  font-size: 0.72rem !important;
  letter-spacing: .08em !important;
  text-transform: uppercase !important;
  font-weight: 700 !important;
}
[data-testid="stSidebar"] .nu-section-icon {
  width: 28px !important; height: 28px !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stLinkButton > a {
  background: transparent !important;
  border: 1px solid #3A415F !important;
  color: #E8EAF2 !important;
  border-radius: 10px !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] .stLinkButton > a:hover {
  color: #FFFFFF !important;
  border-color: #6D5EF5 !important;
}
[data-testid="stSidebar"] [data-testid="stTextInputRootElement"],
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  background: #252A45 !important;
  border: 1px solid #3A415F !important;
  box-shadow: none !important;
  color: #E8EAF2 !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
  background: #32375A !important;
  color: #E8EAF2 !important;
}

/* ---------- Misc ---------- */
[data-testid="stExpander"] {
  border: 1px solid var(--pc-line) !important;
  border-radius: 12px;
  background: #FFFFFF;
  box-shadow: none;
}
[data-testid="stAlert"] {
  border: 1px solid var(--pc-line) !important;
  border-radius: 12px;
  box-shadow: none;
}
[data-testid="stDialog"] div[role="dialog"] {
  border-radius: 16px;
  border: 1px solid var(--pc-line);
  background: #FFFFFF;
  box-shadow: 0 24px 60px rgba(31,36,51,.18);
}
[data-testid="stProgress"] > div > div {
  background: var(--pc-accent) !important;
}

/* Soft pastel badges */
span[data-testid="stBadge"] {
  border-radius: 999px !important;
  font-weight: 600 !important;
  font-size: 0.7rem !important;
  letter-spacing: .02em;
  text-transform: uppercase;
}

.ms {
  font-family: 'Material Symbols Rounded';
  font-weight: 500;
  font-style: normal;
  line-height: 1;
  display: inline-block;
  -webkit-font-smoothing: antialiased;
}

/* ---------- Page header ---------- */
.pc-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-top: 0;
  margin-bottom: 18px;
}
.pc-header-title {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -.03em;
  color: var(--pc-text);
}
.pc-header-sub {
  margin: 6px 0 0 0;
  color: var(--pc-muted);
  font-size: 0.92rem;
  font-weight: 400;
}
.pc-header-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--pc-muted);
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
  padding-top: 6px;
}

/* ---------- Chips ---------- */
.nu-chip-row, .pc-chip-row {
  display: flex; flex-wrap: wrap; gap: 8px;
  margin: 0 0 16px 0;
}
.nu-chip, .pc-chip {
  padding: 5px 12px;
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 600;
  background: #FFFFFF;
  border: 1px solid var(--pc-line);
  box-shadow: none;
  color: #4A5168;
}

/* ---------- KPI ---------- */
.nu-kpi-grid, .pc-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
  gap: 12px;
  margin: 0 0 8px 0;
}
.nu-kpi, .pc-kpi {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 14px;
  background: #FFFFFF;
  border: 1px solid var(--pc-line);
  box-shadow: var(--pc-shadow);
  min-width: 0;
  overflow: hidden;
  transition: none;
}
.nu-kpi:hover, .pc-kpi:hover { transform: none; }
.nu-kpi-icon, .pc-kpi-icon {
  flex: 0 0 auto;
  width: 36px; height: 36px;
  border-radius: 10px;
  display: grid; place-items: center;
  font-size: 20px;
  box-shadow: none;
}
.nu-kpi-body, .pc-kpi-body { min-width: 0; flex: 1 1 auto; }
.nu-kpi-label, .pc-kpi-label {
  font-size: .65rem; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; color: var(--pc-muted); margin-bottom: 4px;
}
.nu-kpi-value, .pc-kpi-value {
  font-size: 1.35rem; font-weight: 700; color: var(--pc-text);
  letter-spacing: -.02em; line-height: 1.15;
}
.nu-kpi-sub, .pc-kpi-sub {
  font-size: .72rem; color: var(--pc-muted); margin-top: 3px; font-weight: 400;
}
.nu-kpi-label, .nu-kpi-value, .nu-kpi-sub,
.pc-kpi-label, .pc-kpi-value, .pc-kpi-sub {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ---------- Section ---------- */
.nu-section, .pc-section {
  display: flex; align-items: center; gap: 10px;
  margin: 2px 0 12px 2px;
}
.nu-section-icon, .pc-section-icon {
  width: 28px; height: 28px; border-radius: 8px;
  display: grid; place-items: center; font-size: 16px;
  box-shadow: none;
}
.nu-section-title, .pc-section-title {
  font-size: 0.95rem; font-weight: 600; color: var(--pc-text); letter-spacing: -.01em;
}

/* ---------- Property table rows ---------- */
.pc-table-head, .pc-table-row {
  display: grid;
  grid-template-columns: 72px minmax(160px, 1.6fr) minmax(110px, 1fr) 100px 90px 120px 130px;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
}
.pc-table-head {
  border-bottom: 1px solid var(--pc-line);
  margin: 0 4px;
}
.pc-table-head span {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--pc-muted);
}
.pc-table-row {
  border-bottom: 1px solid var(--pc-line);
  margin: 0 4px;
}
.pc-table-row:last-of-type { border-bottom: none; }
.pc-table-row:hover { background: #FAFBFE; border-radius: 10px; }
.pc-thumb {
  width: 56px; height: 56px;
  border-radius: 8px;
  object-fit: cover;
  background: #EEF0F6;
}
.pc-prop-name {
  font-weight: 600; color: var(--pc-text); font-size: 0.9rem; line-height: 1.25;
}
.pc-prop-sub {
  color: var(--pc-muted); font-size: 0.75rem; margin-top: 2px;
}
.pc-cell { font-size: 0.875rem; color: var(--pc-text); font-weight: 500; }
.pc-cell-strong { font-size: 0.9rem; color: var(--pc-text); font-weight: 700; }
.pc-match {
  display: flex; flex-direction: column; gap: 4px;
}
.pc-match-val { font-size: 0.85rem; font-weight: 600; color: var(--pc-text); }
.pc-match-bar {
  height: 6px; border-radius: 999px; background: #EBEAF8; overflow: hidden;
}
.pc-match-fill {
  height: 100%; border-radius: 999px; background: var(--pc-accent);
}
.pc-verdict {
  display: inline-flex; align-items: center;
  padding: 4px 10px; border-radius: 999px;
  font-size: 0.68rem; font-weight: 700; letter-spacing: .03em;
  text-transform: uppercase;
}
.pc-verdict-visit { background: #E6F4F1; color: #2F7A6E; }
.pc-verdict-save { background: #E8F0FC; color: #3A6FC4; }
.pc-verdict-reject { background: #F7E9EB; color: #B04E58; }
.pc-verdict-other { background: #EEF0F6; color: #5A6278; }
.pc-table-foot {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 20px 8px; color: var(--pc-muted); font-size: 0.8rem;
}
.pc-open-btn button {
  min-width: 36px !important;
  width: 36px !important;
  height: 36px !important;
  padding: 0 !important;
  border-radius: 8px !important;
}
</style>
"""


def inject() -> None:
    st.html(_CSS)


def card(key: str, **kwargs):
    return st.container(border=True, key=f"nucard_{key}", **kwargs)


def _icon_style(accent: str) -> str:
    bg, fg = ACCENTS.get(accent, ACCENTS["violet"])
    return f"background:{bg};color:{fg}"


def hero(title: str, subtitle: str, icon: str = "dashboard", accent: str = "violet") -> None:
    """Page header matching the portfolio mockup (title + subtitle, no giant card)."""
    del icon, accent  # kept for call-site compatibility
    st.html(
        f"""
        <div class="pc-header">
          <div>
            <div class="pc-header-title">{_html.escape(title)}</div>
            <div class="pc-header-sub">{_html.escape(subtitle)}</div>
          </div>
          <div class="pc-header-meta">
            <span class="ms" style="font-size:16px;vertical-align:middle">sync</span>
            Synced from Google Sheets
          </div>
        </div>
        """
    )


def _kpi_html(label: str, value: str, icon: str, accent: str = "violet", sub: str = "") -> str:
    sub_html = (
        f'<div class="pc-kpi-sub" title="{_html.escape(sub)}">{_html.escape(sub)}</div>'
        if sub
        else ""
    )
    return f"""
        <div class="pc-kpi">
          <div class="pc-kpi-icon" style="{_icon_style(accent)}">
            <span class="ms">{_html.escape(icon)}</span>
          </div>
          <div class="pc-kpi-body">
            <div class="pc-kpi-label">{_html.escape(label)}</div>
            <div class="pc-kpi-value" title="{_html.escape(value)}">{_html.escape(value)}</div>
            {sub_html}
          </div>
        </div>
    """


def kpi(label: str, value: str, icon: str, accent: str = "violet", sub: str = "") -> None:
    st.html(_kpi_html(label, value, icon, accent, sub))


def kpi_grid(cards: list[tuple[str, str, str, str, str]], min_width: str = "168px") -> None:
    inner = "".join(_kpi_html(*card) for card in cards)
    st.html(
        f'<div class="pc-kpi-grid" style="grid-template-columns:'
        f'repeat(auto-fit,minmax({min_width},1fr))">{inner}</div>'
    )


def section(title: str, icon: str, accent: str = "violet") -> None:
    st.html(
        f"""
        <div class="pc-section">
          <div class="pc-section-icon" style="{_icon_style(accent)}">
            <span class="ms">{_html.escape(icon)}</span>
          </div>
          <div class="pc-section-title">{_html.escape(title)}</div>
        </div>
        """
    )


def chips(items: list[str]) -> None:
    if not items:
        return
    inner = "".join(f'<span class="pc-chip">{_html.escape(str(i))}</span>' for i in items)
    st.html(f'<div class="pc-chip-row">{inner}</div>')


def table_header(columns: list[str]) -> None:
    cells = "".join(f"<span>{_html.escape(c)}</span>" for c in columns)
    st.html(f'<div class="pc-table-head">{cells}</div>')


def verdict_class(verdict: str) -> str:
    return {
        "Worth visiting": "pc-verdict-visit",
        "Save": "pc-verdict-save",
        "Reject": "pc-verdict-reject",
    }.get(verdict, "pc-verdict-other")
