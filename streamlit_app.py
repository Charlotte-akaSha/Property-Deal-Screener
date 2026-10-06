"""Property Screener — analyze listings and compare your Google Sheet portfolio."""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_default_favicon = ROOT / "static" / "favicon-light.svg"
st.set_page_config(
    page_title="Property Screener",
    page_icon=str(_default_favicon) if _default_favicon.is_file() else ":material/home_work:",
    layout="wide",
)

import theme_css  # noqa: E402

theme_css.inject()

page = st.navigation(
    [
        st.Page("app_pages/analyze.py", title="Analyze", icon=":material/auto_awesome:"),
        st.Page("app_pages/compare.py", title="Compare", icon=":material/dashboard:"),
    ],
    position="top",
)

page.run()
