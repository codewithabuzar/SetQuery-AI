"""Sidebar controls for SetQuery AI."""

from datetime import date, timedelta
from pathlib import Path
import time
import streamlit as st
from ui import (
    section,
    sensor_text,
    render_status,
    render_legend,
    metric_grid,
    render_before_after_compare,
    open_workspace,
    open_home,
    clear_analysis,
    build_location_from_click,
    search_locations,
    perform_location_search,
    build_study_area_map,
    grouped_bar_chart,
    modern_land_cover_chart,
    historical_index_chart,
    trend_composition_chart,
    render_burn_evidence_tab,
    render_vegetation_stress_tab,
    render_flood_evidence_tab,
    render_ai_qa_section,
    SESSION_DEFAULTS,
    initialize_session_state,
)
from analysis import AnalysisValidationError, AnalysisDataError
from historical_analysis import HistoricalValidationError, HistoricalDataError
from analysis_router import run_routed_analysis, choose_analysis_mode
from trend_analysis import analyze_trend
from flood_analysis import analyze_flood_evidence, FloodValidationError, FloodDataError
from report import generate_analysis_summary, get_coverage_interpretation
from historical_report import (
    generate_historical_summary,
    get_historical_coverage_level,
    get_historical_source_support,
    get_historical_support_warnings,
)

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




def render_sidebar():
    with st.sidebar:

        st.markdown(
            '<div class="sq-brand">'
            '<div class="sq-brand-name">SetQuery</div>'
            '<div class="sq-brand-sub">Satellite change analysis</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sq-sidebar-section">Analysis</div>', unsafe_allow_html=True)

        analysis_type = st.selectbox(
            "Analysis type",
            options=["Compare two dates", "View trend over time"],
            index=0,
            help="Compare two dates measures change between Before and After periods.",
        )

        st.markdown("### Location")

        location_name = st.text_input(
            "Search place",
            placeholder="Powai Lake, Mumbai",
            help="Search for a city, locality, landmark, campus, lake, village, or another named place.",
            key="location_search_input",
        )

        if st.button("Find location", use_container_width=True, key="find_location_btn"):
            perform_location_search(location_name)

        if st.session_state.location_search_error:
            st.warning(st.session_state.location_search_error)

        matches = st.session_state.location_matches

        if st.session_state.pop("reset_location_index", False):
            st.session_state.selected_location_index = 0

        if matches:
            selected_index = st.selectbox(
                "Matching location",
                options=range(len(matches)),
                format_func=lambda index: matches[index]["address"],
                key="selected_location_index",
            )

            st.session_state.selected_location = matches[selected_index]
            st.session_state.location_source = "search"

            selected_location = st.session_state.selected_location

            st.caption(
                f"Selected: {selected_location['latitude']:.5f}, "
                f"{selected_location['longitude']:.5f}"
            )

        if (
            st.session_state.location_source == "click"
            and st.session_state.clicked_latitude is not None
            and st.session_state.clicked_longitude is not None
        ):
            st.success(
                f"📍 Map click: {st.session_state.clicked_latitude:.5f}, "
                f"{st.session_state.clicked_longitude:.5f}"
            )

        st.markdown("### Dates")

        if analysis_type == "Compare two dates":

            before_date = st.date_input("Before", value=date(2022, 9, 15))
            after_date = st.date_input("After", value=date(2025, 9, 15))

        else:

            st.caption(
                "Trend mode analyzes each date independently using "
                "Sentinel-2 + Dynamic World. Dates must be on or after "
                f"{TREND_MIN_DATE.isoformat()} and at least 90 days apart."
            )

            trend_point_count = int(
                st.number_input(
                    "Number of time points",
                    min_value=TREND_MIN_POINTS,
                    max_value=TREND_MAX_POINTS,
                    value=3,
                    step=1,
                )
            )

            today = date.today()
            trend_dates = []

            for point_index in range(trend_point_count):
                default_date = today - timedelta(days=((trend_point_count - 1 - point_index) * 365))

                if default_date < TREND_MIN_DATE:
                    default_date = TREND_MIN_DATE + timedelta(days=point_index * 30)

                picked_date = st.date_input(
                    f"Date {point_index + 1}",
                    value=default_date,
                    min_value=TREND_MIN_DATE,
                    max_value=today,
                    key=f"trend_date_{point_index}",
                )

                trend_dates.append(picked_date)

        st.markdown("### Study Area")

        radius_km = st.slider(
            "Radius",
            min_value=RADIUS_MIN_KM,
            max_value=RADIUS_MAX_KM,
            value=RADIUS_DEFAULT_KM,
            format="%d km",
        )
        st.caption("Circular study area around the selected center.")

        if analysis_type == "Compare two dates":
            predicted_mode = choose_analysis_mode(before_date, after_date)
            st.caption(
                "Sentinel-2 + Dynamic World" if predicted_mode == "modern_ml" else "Landsat historical analysis"
            )
        else:
            st.caption("Sentinel-2 + Dynamic World · independent per-date analysis")

        st.markdown("### Run")

        has_location = (
            st.session_state.selected_location is not None
            or (
                st.session_state.clicked_latitude is not None
                and st.session_state.clicked_longitude is not None
            )
        )

        run_clicked = st.button(
            "Analyze",
            type="primary",
            use_container_width=True,
            disabled=not has_location,
        )

        if st.session_state.analysis_data is not None or st.session_state.trend_data is not None:
            st.button("Clear analysis", use_container_width=True, on_click=clear_analysis)

        st.markdown('<div class="sq-sidebar-rule"></div>', unsafe_allow_html=True)

        st.caption("Target dates represent composite windows, not exact acquisition dates.")
        st.caption("Place search selects the center of a circular study area, not the place's exact boundary.")

        st.button("Back to home", use_container_width=True, on_click=open_home)

    return {
        "analysis_type": analysis_type,
        "before_date": locals().get("before_date"),
        "after_date": locals().get("after_date"),
        "trend_dates": locals().get("trend_dates"),
        "radius_km": radius_km,
        "run_clicked": run_clicked,
    }
