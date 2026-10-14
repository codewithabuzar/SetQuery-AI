"""
SetQuery AI — Satellite Change Detection & Grounded Analysis

Main entry point for the Streamlit application.
All UI components are organized in the ui/ module.
"""

from datetime import date, timedelta
from pathlib import Path
import time

import streamlit as st

# Import from organized UI module
from ui.state import SESSION_DEFAULTS
from ui.helpers import open_workspace

# ==========================================================
# CONFIGURATION
# ==========================================================

CONFIDENCE_THRESHOLD = 0.60
RADIUS_MIN_KM = 1
RADIUS_MAX_KM = 20
RADIUS_DEFAULT_KM = 10
TREND_MIN_POINTS = 2
TREND_MAX_POINTS = 8
TREND_MIN_DATE = date(2017, 1, 1)

CHANGE_LEGEND = [
    ("#ff3b30", "Vegetation → Built"),
    ("#30d158", "Built → Vegetation"),
    ("#ff9f0a", "Bare → Built"),
    ("#2997ff", "Non-water → Water"),
    ("#ff6482", "Water → Non-water"),
]

HOME_PAGE_CSS = """
<style>
section[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
.block-container {
    max-width: 1180px !important;
    padding-top: 5rem !important;
    padding-left: 4rem !important;
    padding-right: 4rem !important;
}
</style>
"""


# ==========================================================
# PAGE SETUP
# ==========================================================

st.set_page_config(
    page_title="SetQuery",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================================
# STYLES
# ==========================================================

STYLE_PATH = Path(__file__).parent / "assets" / "style.css"

if STYLE_PATH.exists():
    st.markdown(f"<style>{STYLE_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# ==========================================================
# SESSION STATE
# ==========================================================

for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================================
# LANDING PAGE
# ==========================================================

if st.session_state.app_view == "home":

    st.markdown(HOME_PAGE_CSS, unsafe_allow_html=True)
    st.markdown('<div class="sq-home-brand">SetQuery</div>', unsafe_allow_html=True)
    st.markdown('<div class="sq-home-space"></div>', unsafe_allow_html=True)

    st.title("Satellite change analysis")
    st.markdown(
        "Compare a place across time using satellite imagery and measured "
        "land-cover or spectral change."
    )
    st.caption("Sentinel-2 · Dynamic World · Landsat · Google Earth Engine")

    st.markdown('<div class="sq-home-button-space"></div>', unsafe_allow_html=True)
    st.button("Open analysis", key="open_analysis", type="primary", on_click=open_workspace)
    st.stop()


if st.session_state.get("navigation_loading"):
    st.session_state.navigation_loading = False

from ui.floating_ai import render_floating_ai

render_floating_ai()

# Professional PDF Report Workspace
# Loaded only after entering the analysis workspace.

workspace_view = st.segmented_control(
    "Workspace",
    ["Satellite Analysis", "Reports"],
    default="Satellite Analysis",
    key="sq_workspace_navigation",
    label_visibility="collapsed",
)

if workspace_view == "Reports":
    from report_workspace_staging import render_report_workspace

    render_report_workspace()
    st.stop()


# Professional PDF Report Workspace
# Loaded only after entering the analysis workspace.




from app_components.sidebar import render_sidebar

sidebar_inputs = render_sidebar()

analysis_type = sidebar_inputs["analysis_type"]
before_date = sidebar_inputs["before_date"]
after_date = sidebar_inputs["after_date"]
trend_dates = sidebar_inputs["trend_dates"]
radius_km = sidebar_inputs["radius_km"]
run_clicked = sidebar_inputs["run_clicked"]

from app_components.analysis_runner import run_selected_analysis

run_selected_analysis(
    run_clicked=run_clicked,
    analysis_type=analysis_type,
    before_date=before_date,
    after_date=after_date,
    trend_dates=trend_dates,
    radius_km=radius_km,
    confidence_threshold=CONFIDENCE_THRESHOLD,
)

# ==========================================================
# ACTIVE ANALYSIS
# ==========================================================

data = st.session_state.analysis_data
trend_data = st.session_state.trend_data


from app_components.workspace import render_empty_workspace

if data is None and trend_data is None:
    render_empty_workspace(radius_km)

from app_components.trend_results import render_trend_results

if trend_data is not None:
    render_trend_results(trend_data)

from app_components.comparison_results import render_comparison_results

render_comparison_results(data, CHANGE_LEGEND)
