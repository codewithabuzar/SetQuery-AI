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

# Import analysis modules
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


# ==========================================================
# SIDEBAR
# ==========================================================

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


# ==========================================================
# RUN ANALYSIS
# ==========================================================

if run_clicked:

    clear_analysis()

    if st.session_state.location_source == "click" and st.session_state.clicked_latitude:
        selected_location = build_location_from_click(
            st.session_state.clicked_latitude, st.session_state.clicked_longitude
        )
    elif st.session_state.selected_location:
        selected_location = st.session_state.selected_location
    else:
        selected_location = None

    if selected_location is None:
        st.error("Select a location via search or click on the map before analyzing.")

    elif analysis_type == "Compare two dates":

        try:
            with st.spinner("Analyzing satellite data..."):
                start_time = time.perf_counter()
                routed = run_routed_analysis(
                    latitude=selected_location["latitude"],
                    longitude=selected_location["longitude"],
                    before_date=str(before_date),
                    after_date=str(after_date),
                    radius_km=radius_km,
                    confidence_threshold=CONFIDENCE_THRESHOLD,
                )

            elapsed = time.perf_counter() - start_time
            print(f"SetQuery Earth Engine analysis: {elapsed:.1f} seconds")

            st.session_state.analysis_data = {
                "location": selected_location["address"],
                "latitude": selected_location["latitude"],
                "longitude": selected_location["longitude"],
                "radius_km": radius_km,
                "before_date": str(before_date),
                "after_date": str(after_date),
                **routed,
            }

        except (
            AnalysisValidationError,
            HistoricalValidationError,
            AnalysisDataError,
            HistoricalDataError,
            ValueError,
        ) as error:
            st.error(str(error))

        except Exception as error:
            st.error("Analysis could not be completed.")
            with st.expander("Technical details"):
                st.exception(error)

    else:

        try:
            with st.spinner("Analyzing satellite data..."):
                start_time = time.perf_counter()
                trend_result = analyze_trend(
                    latitude=selected_location["latitude"],
                    longitude=selected_location["longitude"],
                    dates=[str(single_date) for single_date in trend_dates],
                    radius_km=radius_km,
                    confidence_threshold=CONFIDENCE_THRESHOLD,
                )

            elapsed = time.perf_counter() - start_time
            print(f"SetQuery Earth Engine trend analysis: {elapsed:.1f} seconds")

            st.session_state.trend_data = {
                "location": selected_location["address"],
                "latitude": selected_location["latitude"],
                "longitude": selected_location["longitude"],
                "radius_km": radius_km,
                **trend_result,
            }

        except (
            AnalysisValidationError,
            AnalysisDataError,
            ValueError,
        ) as error:
            st.error(str(error))

        except Exception as error:
            st.error("Trend analysis could not be completed.")
            with st.expander("Technical details"):
                st.exception(error)


# ==========================================================
# ACTIVE ANALYSIS
# ==========================================================

data = st.session_state.analysis_data
trend_data = st.session_state.trend_data


# ==========================================================
# EMPTY WORKSPACE
# ==========================================================

if data is None and trend_data is None:

    st.markdown('<div class="sq-workspace-spacer"></div>', unsafe_allow_html=True)
    st.title("Satellite change analysis")

    if st.session_state.clicked_latitude and st.session_state.clicked_longitude:
        center_lat = st.session_state.clicked_latitude
        center_lon = st.session_state.clicked_longitude
        selected_location = build_location_from_click(center_lat, center_lon)
        location_label = selected_location["address"]
    elif st.session_state.selected_location:
        center_lat = st.session_state.selected_location["latitude"]
        center_lon = st.session_state.selected_location["longitude"]
        location_label = st.session_state.selected_location["address"]
        selected_location = st.session_state.selected_location
    else:
        center_lat = 20.5937
        center_lon = 78.9629
        location_label = None
        selected_location = None

    if selected_location is None:
        st.write(
            "Search for a location in the sidebar, "
            "choose the correct match, and set the "
            "analysis period and radius."
        )
        st.caption("Or click anywhere on the map below to set the analysis center.")
        st.caption("Sentinel-2 · Dynamic World · Landsat")
    else:
        st.write(
            "The analysis center is selected. "
            "Set the dates and radius, then run the analysis."
        )
        st.caption(location_label)

    map_key = "study_area_map"
    map_data = build_study_area_map(
        latitude=center_lat,
        longitude=center_lon,
        radius_km=radius_km,
        location_label=location_label,
        allow_click_select=True,
        map_key=map_key,
    )

    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]

        st.session_state.clicked_latitude = clicked_lat
        st.session_state.clicked_longitude = clicked_lon
        st.session_state.location_source = "click"
        st.session_state.selected_location = None
        st.session_state.location_matches = []
        st.session_state.selected_location_index = 0
        st.session_state.location_search_error = None

        st.info(
            f" Location set: {clicked_lat:.5f}, {clicked_lon:.5f} — "
            "Click Analyze in the sidebar to run the analysis."
        )
        st.rerun()

    st.caption(
        "Geographic context only · the outlined circle "
        "is the current study area. Satellite analysis "
        "uses Sentinel-2 or Landsat through Earth Engine."
    )
    st.caption("Sentinel-2 · Dynamic World · Landsat")
    st.stop()


# ==========================================================
# TREND RESULT VIEW
# ==========================================================

if trend_data is not None:

    period_dates = [period["date"] for period in trend_data["periods"]]

    st.markdown(
        '<div class="sq-result-header">'
        f'<div class="sq-location">{trend_data["location"]}</div>'
        f'<div class="sq-meta">{period_dates[0]} → {period_dates[-1]} '
        f'&nbsp;·&nbsp; {len(period_dates)} time points &nbsp;·&nbsp; '
        f'{trend_data["radius_km"]} km radius</div>'
        '<div class="sq-result-context">Modern ML Trend &nbsp;·&nbsp; ~10 m</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    section("Study area", "Geographic context", "Interactive reference map showing the selected analysis center.")

    build_study_area_map(
        latitude=trend_data["latitude"],
        longitude=trend_data["longitude"],
        radius_km=trend_data["radius_km"],
        location_label=trend_data["location"],
        allow_click_select=False,
        map_key="trend_study_area_map",
    )

    st.caption("Basemap detail is for geographic context only. SetQuery measurements use Sentinel-2 and Dynamic World.")
    st.divider()

    section("Results", "Land-cover trend", trend_data["methodology_note"])

    st.info(
        "Each date below is analyzed independently. Faded "
        "points had low comparable coverage for that specific "
        "date and should be interpreted with caution."
    )

    st.altair_chart(trend_composition_chart(trend_data), width="stretch")
    st.caption("Percent values are relative to each date's own valid area.")

    st.divider()
    section("Details", "Per-date measurements")

    table_rows = [
        {
            "Date": period["date"],
            "Reliable": "Yes" if period["reliable"] else "No",
            "Coverage %": round(period["coverage_percent"], 1),
            "Observations": period["observations"],
            "Vegetation km²": round(period["vegetation_km2"], 3),
            "Built-up km²": round(period["built_km2"], 3),
            "Water km²": round(period["water_km2"], 3),
            "Bare km²": round(period["bare_km2"], 3),
        }
        for period in trend_data["periods"]
    ]

    st.dataframe(table_rows, width="stretch", hide_index=True)

    st.divider()
    section("Query", "Ask SetQuery AI")

    with st.popover("Ask SetQuery AI", use_container_width=False):
        st.caption(
            "Ask SetQuery is not yet available for trend "
            "results. Use Compare two dates for Q&A."
        )

    if trend_data.get("warnings"):
        st.divider()
        section("Notes", "Warnings")
        for warning in trend_data["warnings"]:
            st.warning(warning)

    st.divider()
    with st.expander("Methodology and metadata"):
        st.write(f"Total study area: `{trend_data['total_area_km2']:.2f} km²`")
        st.write(f"Classification method: `{trend_data['classification_method']}`")

    st.markdown('<div class="sq-footer">SetQuery · Satellite change analysis</div>', unsafe_allow_html=True)
    st.stop()


# ==========================================================
# COMPARISON RESULT VIEW
# ==========================================================

mode = data["mode"]
result = data["result"]
images = data["images"]
location = data["location"]
latitude = data["latitude"]
longitude = data["longitude"]
before = data["before_date"]
after = data["after_date"]
radius = data["radius_km"]

st.markdown(
    '<div class="sq-result-header">'
    f'<div class="sq-location">{location}</div>'
    f'<div class="sq-meta">{before} → {after} &nbsp;·&nbsp; {radius} km radius</div>'
    f'<div class="sq-result-context">{data["mode_label"]} &nbsp;·&nbsp; '
    f'~{data["approximate_resolution_m"]} m</div>'
    '</div>',
    unsafe_allow_html=True,
)

section("Study area", "Interactive map", "Zoom and pan to explore. Toggle Earth Engine layers via top-right control.")

build_study_area_map(
    latitude=latitude,
    longitude=longitude,
    radius_km=radius,
    location_label=location,
    tile_layers=data.get("tile_layers"),
    mode=mode,
    allow_click_select=False,
    map_key="result_study_area_map",
)

if mode == "modern_ml":
    st.caption(
        "Interactive Earth Engine layers: Before/After Sentinel-2 and Change Map. "
        "Satellite analysis uses Sentinel-2 (~10 m) and Dynamic World."
    )
else:
    st.caption(
        "Basemap detail is for geographic context only. "
        "SetQuery measurements use Landsat (~30 m) spectral analysis."
    )

st.divider()

# ==========================================================
# MODERN RESULTS
# ==========================================================

if mode == "modern_ml":

    coverage = result["coverage_percent"]
    coverage_info = get_coverage_interpretation(coverage)
    coverage_level = coverage_info["level"]

    render_status(
        f"{coverage_level} coverage · {coverage:.1f}% comparable · {coverage_info['description']}",
        coverage_level,
    )

    section("Imagery", "Change map", "Dynamic World transitions over the after-period Sentinel-2 composite.")

    change_tab, before_tab, after_tab, compare_tab, burn_tab, veg_tab, flood_tab = st.tabs(
        ["Change map", "Before", "After", "Compare", "Burn evidence", "Vegetation stress", "Flood evidence"]
    )

    with change_tab:
        st.image(data["change_map"]["change_url"], width="stretch")
        render_legend(CHANGE_LEGEND)
        st.caption("Displayed change pixels may be enlarged. Area statistics use original pixels.")

    render_before_after_compare(
        (before_tab, after_tab, compare_tab),
        before_url=images["before_url"],
        after_url=images["after_url"],
        before_caption=f"{images['before_sentinel_observations']} Sentinel-2 observations",
        after_caption=f"{images['after_sentinel_observations']} Sentinel-2 observations",
        before=before,
        after=after,
    )

    with burn_tab:
        render_burn_evidence_tab(latitude, longitude, before, after, radius)

    with veg_tab:
        render_vegetation_stress_tab(latitude, longitude, before, after, radius)

    with flood_tab:
        render_flood_evidence_tab(latitude, longitude, before, after, radius)

    st.divider()
    section("Results", "Land cover", "Measurements from pixels passing temporal-consensus in both periods.")

    vegetation_change = result["after_vegetation_km2"] - result["before_vegetation_km2"]
    built_change = result["after_built_km2"] - result["before_built_km2"]

    metric_grid(
        [
            ("Coverage", f"{coverage:.1f}%"),
            ("Comparable area", f"{result['comparable_area_km2']:.2f} km²"),
            ("Vegetation", f"{vegetation_change:+.3f} km²"),
            ("Built-up", f"{built_change:+.3f} km²"),
        ],
        per_row=4,
    )

    st.altair_chart(modern_land_cover_chart(result), width="stretch")

    before_values, after_values = st.columns(2)

    with before_values:
        st.markdown(f"### Before · {before}")
        metric_grid([
            ("Vegetation", f"{result['before_vegetation_km2']:.2f} km²"),
            ("Built-up", f"{result['before_built_km2']:.2f} km²"),
            ("Water", f"{result['before_water_km2']:.2f} km²"),
            ("Bare", f"{result['before_bare_km2']:.2f} km²"),
        ])

    with after_values:
        st.markdown(f"### After · {after}")
        metric_grid([
            ("Vegetation", f"{result['after_vegetation_km2']:.2f} km²"),
            ("Built-up", f"{result['after_built_km2']:.2f} km²"),
            ("Water", f"{result['after_water_km2']:.2f} km²"),
            ("Bare", f"{result['after_bare_km2']:.2f} km²"),
        ])

    st.divider()
    section("Details", "Transitions", "Explicit class transitions differ from net land-cover differences.")

    metric_grid(
        [
            ("Vegetation → Built", f"{result['vegetation_to_built_km2']:.4f} km²"),
            ("Built → Vegetation", f"{result['built_to_vegetation_km2']:.4f} km²"),
            ("Bare → Built", f"{result['bare_to_built_km2']:.4f} km²"),
        ],
        per_row=3,
    )

    metric_grid(
        [
            ("Water → Non-water", f"{result['water_to_nonwater_km2']:.4f} km²"),
            ("Non-water → Water", f"{result['nonwater_to_water_km2']:.4f} km²"),
        ],
        per_row=2,
    )

    summary = generate_analysis_summary(location=location, before_date=before, after_date=after, result=result)


# ==========================================================
# HISTORICAL RESULTS
# ==========================================================

else:

    coverage = result["coverage_percent"]
    coverage_level = get_historical_coverage_level(coverage)
    source_support = get_historical_source_support(result)

    render_status(
        f"{coverage_level} spatial coverage · {coverage:.1f}% comparable. "
        "Historical results are spectral-index measurements.",
        coverage_level,
    )

    section("Data", "Source support", "Coverage describes valid spatial comparison.")

    metric_grid(
        [
            ("Coverage", f"{coverage:.1f}%"),
            ("Before support", source_support["before_level"], f"{source_support['before_count']} obs."),
            ("After support", source_support["after_level"], f"{source_support['after_count']} obs."),
        ],
        per_row=3,
    )

    for warning in get_historical_support_warnings(result):
        st.warning(warning)

    st.divider()
    section("Imagery", "Landsat comparison")

    tabs = st.tabs(["Before", "After", "Compare"])

    render_before_after_compare(
        tabs,
        before_url=images["before_url"],
        after_url=images["after_url"],
        before_caption=sensor_text(images["before_sensors"]),
        after_caption=sensor_text(images["after_sensors"]),
        before=before,
        after=after,
    )

    st.divider()
    section("Results", "Spectral comparison", "NDVI (vegetation), MNDWI (water), NDBI (built/bare).")

    metric_grid(
        [
            ("Comparable area", f"{result['comparable_area_km2']:.2f} km²"),
            ("NDVI", f"{result['ndvi_change']:+.3f}"),
            ("MNDWI", f"{result['mndwi_change']:+.3f}"),
            ("NDBI", f"{result['ndbi_change']:+.3f}"),
        ],
        per_row=4,
    )

    st.altair_chart(historical_index_chart(result), width="stretch")

    before_indices, after_indices = st.columns(2)

    with before_indices:
        st.markdown(f"### Before · {before}")
        st.metric("NDVI", f"{result['before_mean_ndvi']:.3f}")
        st.metric("MNDWI", f"{result['before_mean_mndwi']:.3f}")
        st.metric("NDBI", f"{result['before_mean_ndbi']:.3f}")

    with after_indices:
        st.markdown(f"### After · {after}")
        st.metric("NDVI", f"{result['after_mean_ndvi']:.3f}")
        st.metric("MNDWI", f"{result['after_mean_mndwi']:.3f}")
        st.metric("NDBI", f"{result['after_mean_ndbi']:.3f}")

    for warning in result.get("warnings", []):
        st.warning(warning)

    summary = generate_historical_summary(location=location, before_date=before, after_date=after, result=result)


# ==========================================================
# SUMMARY & AI
# ==========================================================

st.divider()
section("Summary", "Analysis")
st.write(summary)

st.divider()
section("Query", "Ask SetQuery AI", "Ask a question about the current analysis.")

render_ai_qa_section(mode, result, location, before, after)

# ==========================================================
# METHODOLOGY
# ==========================================================

st.divider()

with st.expander("Methodology and metadata"):

    metadata_left, metadata_right = st.columns(2)

    with metadata_left:
        st.markdown("#### Study")
        st.write(f"Mode: `{data['mode_label']}`")
        st.write(f"Method: `{data['method']}`")
        st.write(f"Resolution: `~{data['approximate_resolution_m']} m`")
        st.write(f"Latitude: `{latitude:.5f}`")
        st.write(f"Longitude: `{longitude:.5f}`")
        st.write(f"Radius: `{radius} km`")

    with metadata_right:
        st.markdown("#### Time")
        st.write(f"Before target: `{before}`")
        st.write(f"After target: `{after}`")
        if result.get("date_separation_days") is not None:
            st.write(f"Target separation: `{result['date_separation_days']} days`")

    if mode == "modern_ml":
        st.markdown("#### Temporal consensus")
        st.write(f"Per-observation probability: `≥ {result.get('confidence_threshold', 0.60) * 100:.0f}%`")
        st.write(f"Minimum confident observations: `{result.get('min_confident_observations', 2)}`")
        st.write(f"Dynamic World observations: `{result['before_observations']} / {result['after_observations']}`")
    else:
        st.markdown("#### Landsat")
        st.write("Before: " + sensor_text(result["before_sensors"]))
        st.write("After: " + sensor_text(result["after_sensors"]))

    st.markdown(
        """
#### Limits

Comparable coverage is not classification accuracy.
Target dates are composite centers rather than exact
acquisition dates. Results are satellite-derived
estimates rather than surveyed ground truth.
"""
    )


# ==========================================================
# FOOTER
# ==========================================================

st.markdown('<div class="sq-footer">SetQuery · Satellite change analysis</div>', unsafe_allow_html=True)