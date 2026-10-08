"""Portfolio comparison design system — clean SaaS glass, not neumorphism."""

from __future__ import annotations

import html as _html
import inspect

import streamlit as st
import streamlit.components.v1 as components

# Soft pastel accents for KPI icon wells (tint, icon)
ACCENTS = {
    "violet": ("#EFEBFB", "#6D5EF5"),
    "mint": ("#E6F4F1", "#3D9B8F"),
    "blue": ("#E8F0FC", "#5B8DEF"),
    "peach": ("#F8EEE6", "#D4924A"),
    "rose": ("#F7E9EB", "#D4717A"),
    "amber": ("#F6F0E4", "#C9A227"),
}

# Must match len(COMPARE_TABLE_HEADERS) in app_pages/compare.py (17 columns).
COMPARE_GRID_TEMPLATE = (
    "minmax(220px, 260px) minmax(152px, 1.15fr) 92px 76px 76px 72px 48px "
    "minmax(124px, 1fr) 70px 92px 108px minmax(120px, 1fr) 108px 78px 78px 58px 118px"
)


def compare_grid_style_attr() -> str:
    return f' style="grid-template-columns:{COMPARE_GRID_TEMPLATE}"'


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
  width: 48px; height: 48px;
  border-radius: 8px;
  object-fit: cover;
  background: #EEF0F6;
  flex-shrink: 0;
}
.pc-thumb-empty { flex-shrink: 0; }
.pc-sticky-prop {
  position: sticky;
  left: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  background: #fff;
  padding-right: 10px;
  margin-right: 2px;
  box-shadow: 6px 0 10px -8px rgba(30, 35, 55, 0.35);
}
.pc-sticky-head {
  z-index: 4;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--pc-muted);
  box-shadow: none;
  padding-right: 0;
}
.pc-sticky-prop-text {
  min-width: 0;
  flex: 1;
  overflow: hidden;
}
.pc-sticky-prop-text .pc-prop-name,
.pc-sticky-prop-text .pc-prop-link {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pc-prop-name {
  font-weight: 600; color: var(--pc-text); font-size: 0.9rem; line-height: 1.25;
}
a.pc-prop-link {
  color: var(--pc-text);
  text-decoration: none;
}
a.pc-prop-link:hover {
  color: var(--pc-accent);
  text-decoration: underline;
}
.pc-kpi-sub-link {
  display: block;
  font-size: .72rem;
  color: var(--pc-accent);
  margin-top: 3px;
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pc-kpi-sub-link:hover { text-decoration: underline; }
.pc-prop-sub {
  color: var(--pc-muted); font-size: 0.75rem; margin-top: 2px;
}
.pc-hood-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 999px;
  font-size: 0.72rem; font-weight: 600; line-height: 1.35;
  max-width: 100%;
}
.pc-cell-hood-clip {
  overflow: hidden;
  max-width: 100%;
}
.pc-cell-hood-clip .pc-hood-badge {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pc-cell {
  font-size: 0.875rem; color: var(--pc-text); font-weight: 500;
  min-width: 0; max-width: 100%; overflow: hidden;
}
.pc-cell-strong {
  font-size: 0.9rem; color: var(--pc-text); font-weight: 700;
  min-width: 0; max-width: 100%; overflow: hidden;
}
.pc-cell-clip {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.pc-cell-clamp {
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  word-break: break-word;
  line-height: 1.3;
  max-width: 100%;
}
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
.pc-compare-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.pc-compare-head, .pc-compare-row {
  display: grid;
  grid-template-columns: /*COMPARE_GRID_TEMPLATE*/;
  gap: 8px;
  align-items: center;
  min-width: 1872px;
  padding: 8px 10px;
}
.pc-compare-head > *,
.pc-compare-row > * {
  min-width: 0;
}
.pc-compare-head {
  color: var(--pc-muted);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: .04em;
  text-transform: uppercase;
  border-bottom: 1px solid var(--pc-line);
}
.pc-compare-head > span { padding: 2px 0; }
a.pc-sort-link {
  color: var(--pc-muted);
  text-decoration: none;
  cursor: pointer;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
a.pc-sort-link:hover { color: var(--pc-accent); }
a.pc-sort-link.pc-sort-active { color: var(--pc-text); }
.pc-sticky-head.pc-sort-link { display: block; }
.pc-compare-row { border-bottom: 1px solid var(--pc-line); }
.pc-compare-row:hover { background: #FAFBFE; }
.pc-compare-row:hover .pc-sticky-prop { background: #FAFBFE; }
.pc-sticky-verdict {
  position: sticky;
  right: 0;
  z-index: 2;
  min-width: 0;
  background: #fff;
  padding-left: 10px;
  margin-left: 2px;
  box-shadow: -6px 0 10px -8px rgba(30, 35, 55, 0.35);
}
.pc-compare-row:hover .pc-sticky-verdict { background: #FAFBFE; }
a.pc-sort-link.pc-sticky-verdict-head {
  display: block;
  text-align: right;
  box-shadow: none;
  padding-left: 0;
}
.pc-flood-low { color: #2F7A6E; font-weight: 600; }
.pc-flood-mod { color: #9A6B12; font-weight: 600; }
.pc-flood-high { color: #B04E58; font-weight: 600; }
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

_FAVICON_SCRIPT = """
<script>
(function () {
  // Dark browser UI → white icon; light browser UI → dark icon
  const ICON_LIGHT_UI = "/app/static/favicon-light.svg";
  const ICON_DARK_UI = "/app/static/favicon-dark.svg";
  const ICON_ADAPTIVE = "/app/static/favicon.svg";

  function clearForeignIcons() {
    document.querySelectorAll('link[rel*="icon"]:not([data-pc-adaptive-favicon])').forEach(
      (node) => node.remove()
    );
  }

  function applyFavicon() {
    clearForeignIcons();
    document.querySelectorAll("link[data-pc-adaptive-favicon]").forEach((n) => n.remove());

    const adaptive = document.createElement("link");
    adaptive.rel = "icon";
    adaptive.type = "image/svg+xml";
    adaptive.href = ICON_ADAPTIVE;
    adaptive.setAttribute("data-pc-adaptive-favicon", "1");
    document.head.appendChild(adaptive);

    const forLightChrome = document.createElement("link");
    forLightChrome.rel = "icon";
    forLightChrome.type = "image/svg+xml";
    forLightChrome.href = ICON_LIGHT_UI;
    forLightChrome.media = "(prefers-color-scheme: light)";
    forLightChrome.setAttribute("data-pc-adaptive-favicon", "1");
    document.head.appendChild(forLightChrome);

    const forDarkChrome = document.createElement("link");
    forDarkChrome.rel = "icon";
    forDarkChrome.type = "image/svg+xml";
    forDarkChrome.href = ICON_DARK_UI;
    forDarkChrome.media = "(prefers-color-scheme: dark)";
    forDarkChrome.setAttribute("data-pc-adaptive-favicon", "1");
    document.head.appendChild(forDarkChrome);
  }

  applyFavicon();
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyFavicon);
  setTimeout(applyFavicon, 0);
  setTimeout(applyFavicon, 400);
  setTimeout(applyFavicon, 1500);
})();
</script>
"""

_CSS = _CSS.replace("/*COMPARE_GRID_TEMPLATE*/", COMPARE_GRID_TEMPLATE)


def _st_html(markup: str, *, allow_javascript: bool = False) -> None:
    """st.html with JS on newer Streamlit; components.html fallback on 1.50 and older."""
    if allow_javascript and "unsafe_allow_javascript" not in inspect.signature(st.html).parameters:
        components.html(markup, height=0)
        return
    if allow_javascript:
        st.html(markup, unsafe_allow_javascript=True)
    else:
        st.html(markup)


def inject() -> None:
    _st_html(_CSS)
    _st_html(_FAVICON_SCRIPT, allow_javascript=True)


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


def _kpi_html(
    label: str,
    value: str,
    icon: str,
    accent: str = "violet",
    sub: str = "",
    sub_link: str = "",
) -> str:
    if sub and sub_link and (
        sub_link.startswith("http://") or sub_link.startswith("https://")
    ):
        sub_html = (
            f'<a class="pc-kpi-sub-link" href="{_html.escape(sub_link)}" '
            f'target="_blank" rel="noopener noreferrer" title="{_html.escape(sub)}">'
            f"{_html.escape(sub)}</a>"
        )
    elif sub:
        sub_html = (
            f'<div class="pc-kpi-sub" title="{_html.escape(sub)}">{_html.escape(sub)}</div>'
        )
    else:
        sub_html = ""
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


def kpi_grid(
    cards: list[tuple[str, str, str, str, str] | tuple[str, str, str, str, str, str]],
    min_width: str = "168px",
) -> None:
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


_HOOD_BADGE_BASE = (
    "display:inline-flex;align-items:center;gap:4px;padding:2px 8px;"
    "border-radius:999px;font-size:0.72rem;font-weight:600;line-height:1.35;"
    "max-width:100%;"
)
_HOOD_INLINE: dict[int | None, str] = {
    1: "background:#3A8F82;color:#F4FBFA;",
    2: "background:#D8F0EB;color:#1F6B5F;",
    3: "background:#FFF6DB;color:#8A6A12;",
    4: "background:#FFF0E6;color:#B35A24;",
    5: "background:#F7E9EB;color:#B04E58;",
    None: "background:#EEF0F6;color:#5A6278;",
}


def hood_tier_class(tier: int | None) -> str:
    return {
        1: "pc-hood-p1",
        2: "pc-hood-p2",
        3: "pc-hood-p3",
        4: "pc-hood-p4",
        5: "pc-hood-p5",
    }.get(tier or 0, "pc-hood-unknown")


def hood_tier_badge_html(label: str, tier: int | None) -> str:
    from neighbourhood_tiers import tier_emoji, tier_short_label

    text = str(label or "—").strip() or "—"
    emoji = tier_emoji(tier)
    display = f"{emoji} {text}".strip() if emoji else text
    cls = hood_tier_class(tier)
    tip = tier_short_label(tier)
    title = f' title="{_html.escape(tip)}"' if tip else ""
    style = _HOOD_BADGE_BASE + _HOOD_INLINE.get(tier, _HOOD_INLINE[None])
    return (
        f'<span class="pc-hood-badge {cls}" style="{style}"{title}>'
        f"{_html.escape(display)}</span>"
    )


_FLOOD_INLINE: dict[str, str] = {
    "Low": "background:#E6F4F1;color:#1F6B5F;",
    "Moderate": "background:#FFF6DB;color:#8A6A12;",
    "High": "background:#F7E9EB;color:#B04E58;",
}
_FLOOD_BADGE_BASE = (
    "display:inline-flex;align-items:center;gap:4px;padding:2px 8px;"
    "border-radius:999px;font-size:0.72rem;font-weight:600;line-height:1.35;"
    "max-width:100%;white-space:normal;"
)


def flood_risk_badge_html(display_text: str) -> str:
    text = str(display_text or "—").strip() or "—"
    if text == "—":
        return f'<span style="{_FLOOD_BADGE_BASE}background:#EEF0F6;color:#5A6278;">—</span>'
    label = "High" if "🔴" in text or text.startswith("High") else (
        "Moderate" if "🟡" in text or text.startswith("Moderate") else (
            "Low" if "🟢" in text or text.startswith("Low") else ""
        )
    )
    style = _FLOOD_BADGE_BASE + _FLOOD_INLINE.get(label, "background:#EEF0F6;color:#5A6278;")
    return f'<span class="pc-flood-badge" style="{style}">{_html.escape(text)}</span>'


def chip_row(*fragments: str) -> None:
    if not fragments:
        return
    st.html(f'<div class="pc-chip-row">{"".join(fragments)}</div>')


def chips(items: list[str]) -> None:
    if not items:
        return
    inner = "".join(f'<span class="pc-chip">{_html.escape(str(i))}</span>' for i in items)
    chip_row(inner)


def table_header(columns: list[str]) -> None:
    cells = "".join(f"<span>{_html.escape(c)}</span>" for c in columns)
    st.html(f'<div class="pc-table-head">{cells}</div>')


def verdict_class(verdict: str) -> str:
    return {
        "Worth visiting": "pc-verdict-visit",
        "Strong candidate": "pc-verdict-visit",
        "Buy": "pc-verdict-visit",
        "Save": "pc-verdict-save",
        "Investigate": "pc-verdict-save",
        "Reject": "pc-verdict-reject",
        "Pass": "pc-verdict-reject",
    }.get(verdict, "pc-verdict-other")


def _research_text(source: object, *keys: str) -> str:
    getter = source.get if hasattr(source, "get") else None
    for key in keys:
        raw = getter(key) if getter else None
        text = "" if raw is None else str(raw).strip()
        if text and text.lower() not in {"nan", "none", "—"}:
            return text
    return ""


def render_market_research_sections(source: object) -> None:
    """Neighbourhood / appreciation / rental write-ups from Analyze or a Sheet row."""
    neighbourhood = _research_text(
        source, "neighbourhood_research", "Neighbourhood Research"
    )
    neighbourhood_name = _research_text(source, "neighbourhood_name", "Neighbourhood")
    appreciation = _research_text(
        source, "appreciation_research", "Appreciation Research"
    )
    rental = _research_text(source, "rental_research", "Rental Research")
    if not (neighbourhood or appreciation or rental):
        st.caption(
            "No neighbourhood, appreciation, or rental research yet — "
            "re-analyze this listing to fill these sections."
        )
        return
    hood_title = (
        f"Neighbourhood — {neighbourhood_name}" if neighbourhood_name else "Neighbourhood"
    )
    blocks = [
        ("research_hood", hood_title, "location_on", "mint", neighbourhood),
        ("research_apprec", "Long-term appreciation", "trending_up", "violet", appreciation),
        ("research_rent", "Rental potential", "apartment", "peach", rental),
    ]
    for key, title, icon, accent, body in blocks:
        with card(key):
            section(title, icon, accent)
            st.markdown(body or "—")
