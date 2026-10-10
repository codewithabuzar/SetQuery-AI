from datetime import date, timedelta
from pathlib import Path
import time

import altair as alt
import folium
import requests
import streamlit as st

from folium.plugins import Fullscreen
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

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
    answer_historical_query,
)
from query import answer_query
from llm import ask_gemini, ask_gemini_historical, LLMUnavailableError, LLMConfigurationError


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

GEOCODER_USER_AGENT = "setquery-ai-student-project"
GEOCODER_RESULT_LIMIT = 5
GEOCODER_TIMEOUT_SECONDS = 10
PREVIEW_TIMEOUT_SECONDS = 30
PREVIEW_MAX_ATTEMPTS = 3
PREVIEW_RETRY_DELAY_SECONDS = 1.0

CHANGE_LEGEND = [
    ("#ff0000", "Vegetation → Built"),
    ("#00d45a", "Built → Vegetation"),
    ("#e6c800", "Bare → Built"),
    ("#3278ff", "Non-water → Water"),
    ("#e78134", "Water → Non-water"),
]

AI_SOURCE_CAPTIONS = {
    "gemini": "Generated from the current analysis measurements",
    "gemini-historical": "Generated from the current analysis measurements",
    "historical-local": "Local response from historical analysis measurements",
    "fallback": "Local response from analysis measurements",
}

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

SESSION_DEFAULTS = {
    "app_view": "home",
    "analysis_data": None,
    "trend_data": None,
    "flood_evidence_data": None,
    "flood_evidence_error": None,
    "burn_evidence_data": None,
    "burn_evidence_error": None,
    "vegetation_stress_data": None,
    "vegetation_stress_error": None,
    "ai_answer": None,
    "ai_source": None,
    "ai_status": None,
    "location_matches": [],
    "selected_location": None,
    "selected_location_index": 0,
    "location_search_error": None,
}


# ==========================================================
# PAGE
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
# UI HELPERS
# ==========================================================

def section(label, title, description=None):
    """Render a minimal section heading."""
    if label:
        st.markdown(f'<div class="sq-section-label">{label}</div>', unsafe_allow_html=True)
    st.subheader(title)
    if description:
        st.caption(description)


def sensor_text(sensor_list):
    """Format Landsat sensor metadata."""
    if not sensor_list:
        return "No sensor metadata"
    return ", ".join(f"{item['name']} ({item['observations']} obs.)" for item in sensor_list)


def coverage_status_class(level):
    """Select status style from coverage category."""
    if level == "GOOD":
        return "sq-status-good"
    if level in ("MODERATE", "LIMITED"):
        return "sq-status-warning"
    return "sq-status-danger"


def render_status(text, level):
    """Render restrained analysis-quality status."""
    css_class = coverage_status_class(level)
    st.markdown(f'<div class="sq-status {css_class}">{text}</div>', unsafe_allow_html=True)


def render_legend(items):
    """Render a row of colored legend dots with labels."""
    spans = "".join(
        f'<span class="sq-legend-item">'
        f'<span class="sq-dot" style="background:{color}"></span>{label}</span>'
        for color, label in items
    )
    st.markdown(f'<div class="sq-legend">{spans}</div>', unsafe_allow_html=True)


def metric_grid(items, per_row=2):
    """
    Render metrics in evenly spaced rows.

    Each item is (label, value) or (label, value, delta), matching
    st.metric's positional signature.
    """
    for start in range(0, len(items), per_row):
        row_items = items[start:start + per_row]
        for col, item in zip(st.columns(len(row_items)), row_items):
            col.metric(*item)


def render_before_after_compare(tabs, before_url, after_url, before_caption, after_caption, before, after):
    """Render the shared Before / After / Compare tab pattern used by both analysis modes."""
    before_tab, after_tab, compare_tab = tabs

    with before_tab:
        st.image(before_url, width="stretch")
        st.caption(before_caption)

    with after_tab:
        st.image(after_url, width="stretch")
        st.caption(after_caption)

    with compare_tab:
        col_before, col_after = st.columns(2)
        with col_before:
            st.markdown(f"### Before · {before}")
            st.image(before_url, width="stretch")
        with col_after:
            st.markdown(f"### After · {after}")
            st.image(after_url, width="stretch")


def open_workspace():
    """Open the analysis workspace."""
    st.session_state.app_view = "workspace"


def open_home():
    """Return to the landing page."""
    st.session_state.app_view = "home"


def clear_analysis():
    """Clear current analysis and query state."""
    st.session_state.analysis_data = None
    st.session_state.trend_data = None
    st.session_state.flood_evidence_data = None
    st.session_state.flood_evidence_error = None
    st.session_state.burn_evidence_data = None
    st.session_state.burn_evidence_error = None
    st.session_state.vegetation_stress_data = None
    st.session_state.vegetation_stress_error = None
    st.session_state.ai_answer = None
    st.session_state.ai_source = None
    st.session_state.ai_status = None


# ==========================================================
# LOCATION SEARCH
# ==========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def search_locations(query):
    """
    Search Nominatim for multiple candidate locations.

    Identical searches are cached for one hour to avoid
    unnecessary requests to the public geocoding service.
    """
    query = query.strip()
    if not query:
        return []

    geocoder = Nominatim(user_agent=GEOCODER_USER_AGENT)

    try:
        matches = geocoder.geocode(
            query,
            exactly_one=False,
            limit=GEOCODER_RESULT_LIMIT,
            addressdetails=True,
            timeout=GEOCODER_TIMEOUT_SECONDS,
        )
    except Exception as error:
        raise ValueError(
            "Location search is temporarily unavailable. "
            "Check your connection and try again."
        ) from error

    if not matches:
        return []

    results, seen = [], set()

    for match in matches:
        latitude = float(match.latitude)
        longitude = float(match.longitude)
        address = match.address or query
        key = (round(latitude, 6), round(longitude, 6), address)

        if key in seen:
            continue

        seen.add(key)
        results.append({"address": address, "latitude": latitude, "longitude": longitude})

    return results


def perform_location_search(query):
    """Resolve search text into candidate locations."""
    st.session_state.location_search_error = None
    st.session_state.location_matches = []
    st.session_state.selected_location = None
    st.session_state.selected_location_index = 0

    query = query.strip()
    if not query:
        st.session_state.location_search_error = "Enter a location to search."
        return

    try:
        matches = search_locations(query)
    except ValueError as error:
        st.session_state.location_search_error = str(error)
        return

    if not matches:
        st.session_state.location_search_error = (
            "No matching location was found. Try adding a city, state, or country."
        )
        return

    st.session_state.location_matches = matches
    st.session_state.selected_location = matches[0]


# ==========================================================
# EARTH ENGINE PREVIEW DELIVERY
# ==========================================================

def fetch_preview_image(url, label):
    """
    Download an Earth Engine preview with lightweight retry.

    Preview delivery is kept separate from numerical
    analysis so a failed thumbnail does not invalidate
    successfully calculated measurements.
    """

    if not url:
        return {
            "bytes": None,
            "error": f"{label} preview URL was not generated.",
        }

    last_error = None

    for attempt in range(PREVIEW_MAX_ATTEMPTS):

        try:
            response = requests.get(
                url,
                timeout=PREVIEW_TIMEOUT_SECONDS,
            )

            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type",
                "",
            ).lower()

            if not content_type.startswith("image/"):
                raise ValueError(
                    "Earth Engine returned a non-image response."
                )

            if not response.content:
                raise ValueError(
                    "Earth Engine returned an empty preview."
                )

            return {
                "bytes": response.content,
                "error": None,
            }

        except Exception as error:
            last_error = error

            if attempt < PREVIEW_MAX_ATTEMPTS - 1:
                time.sleep(
                    PREVIEW_RETRY_DELAY_SECONDS
                    * (attempt + 1)
                )

    return {
        "bytes": None,
        "error": (
            f"{label} preview could not be loaded. "
            "The analysis measurements are still available."
        ),
        "technical_error": str(last_error),
    }


def prepare_preview_images(routed):
    """
    Download generated satellite previews immediately after
    analysis so Streamlit displays stable image bytes rather
    than asking the browser to fetch temporary EE URLs.
    """

    images = routed["images"]

    previews = {
        "before": fetch_preview_image(
            images.get("before_url"),
            "Before",
        ),
        "after": fetch_preview_image(
            images.get("after_url"),
            "After",
        ),
        "change": None,
    }

    if (
        routed["mode"] == "modern_ml"
        and routed.get("change_map")
    ):
        previews["change"] = fetch_preview_image(
            routed["change_map"].get("change_url"),
            "Change map",
        )

    return previews


def render_preview(preview):
    """
    Render downloaded image bytes or a controlled warning.
    """

    if preview and preview.get("bytes"):
        st.image(
            preview["bytes"],
            width="stretch",
        )
        return

    if preview:
        message = preview.get(
            "error",
            "Preview is unavailable.",
        )
    else:
        message = "Preview is unavailable."

    st.warning(message)


# ==========================================================
# STUDY AREA MAP
# ==========================================================

def build_study_area_map(
    latitude,
    longitude,
    radius_km,
    location_label=None,
):
    """
    Build an interactive geographic-context map.

    The basemap is for geographic orientation only.
    SetQuery analysis continues to use Earth Engine
    Sentinel-2 / Landsat data.
    """

    latitude = float(latitude)
    longitude = float(longitude)
    radius_km = float(radius_km)

    # A useful initial zoom based on the requested radius.
    if radius_km <= 1:
        zoom_start = 15
    elif radius_km <= 2:
        zoom_start = 14
    elif radius_km <= 5:
        zoom_start = 12
    elif radius_km <= 10:
        zoom_start = 11
    else:
        zoom_start = 10

    map_object = folium.Map(
        location=[
            latitude,
            longitude,
        ],
        zoom_start=zoom_start,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
        scrollWheelZoom=False,
    )

    # Neutral reference basemap.
    folium.TileLayer(
        tiles=(
            "https://{s}.tile.openstreetmap.org/"
            "{z}/{x}/{y}.png"
        ),
        attr="© OpenStreetMap contributors",
        name="Map",
        overlay=False,
        control=True,
        max_zoom=19,
    ).add_to(
        map_object
    )

    # Selected location.
    popup_text = (
        location_label
        if location_label
        else "Selected analysis center"
    )

    folium.CircleMarker(
        location=[
            latitude,
            longitude,
        ],
        radius=5,
        color="#f5f5f7",
        weight=2,
        fill=True,
        fill_color="#ef4444",
        fill_opacity=1,
        tooltip="Analysis center",
        popup=popup_text,
    ).add_to(
        map_object
    )

    # Actual circular AOI used by the current analysis.
    folium.Circle(
        location=[
            latitude,
            longitude,
        ],
        radius=(
            radius_km
            * 1000
        ),
        color="#ef4444",
        weight=2,
        opacity=0.9,
        fill=True,
        fill_color="#ef4444",
        fill_opacity=0.07,
        tooltip=(
            f"{radius_km:g} km analysis radius"
        ),
    ).add_to(
        map_object
    )

    Fullscreen(
        position="topright",
        title="Fullscreen",
        title_cancel="Exit fullscreen",
        force_separate_button=True,
    ).add_to(
        map_object
    )

    folium.LayerControl(
        position="topright",
        collapsed=True,
    ).add_to(
        map_object
    )

    return map_object


# ==========================================================
# CHARTS
# ==========================================================

def _paired_values(result, mapping, category_field, value_field):
    """Flatten before/after result fields into Altair-friendly rows."""
    values = []
    for category, before_key, after_key in mapping:
        values.append({category_field: category, "Period": "Before", value_field: result[before_key]})
        values.append({category_field: category, "Period": "After", value_field: result[after_key]})
    return values


def grouped_bar_chart(values, category_field, category_order, value_field, value_title, tooltip_format=".3f"):
    """Shared Before/After grouped bar chart used by both analysis modes."""
    return (
        alt.Chart(alt.Data(values=values))
        .mark_bar(cornerRadiusTopLeft=1, cornerRadiusTopRight=1)
        .encode(
            x=alt.X(f"{category_field}:N", title=None, sort=category_order),
            xOffset=alt.XOffset("Period:N"),
            y=alt.Y(f"{value_field}:Q", title=value_title),
            color=alt.Color(
                "Period:N",
                scale=alt.Scale(domain=["Before", "After"], range=["#696e72", "#d9dddf"]),
                legend=alt.Legend(orient="top", title=None),
            ),
            tooltip=[
                alt.Tooltip(f"{category_field}:N"),
                alt.Tooltip("Period:N"),
                alt.Tooltip(f"{value_field}:Q", title=value_title, format=tooltip_format),
            ],
        )
        .properties(height=250)
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#8a9095",
            titleColor="#8a9095",
            gridColor="#222629",
            domainColor="#303438",
            tickColor="#303438",
        )
        .configure_legend(labelColor="#a4a9ae")
    )


def modern_land_cover_chart(result):
    """Before/After land-cover chart."""
    mapping = [
        ("Vegetation", "before_vegetation_km2", "after_vegetation_km2"),
        ("Built-up", "before_built_km2", "after_built_km2"),
        ("Water", "before_water_km2", "after_water_km2"),
        ("Bare", "before_bare_km2", "after_bare_km2"),
    ]
    values = _paired_values(result, mapping, "Class", "Area")
    return grouped_bar_chart(values, "Class", ["Vegetation", "Built-up", "Water", "Bare"], "Area", "Area (km²)")


def historical_index_chart(result):
    """Before/After historical spectral-index chart."""
    mapping = [
        ("NDVI", "before_mean_ndvi", "after_mean_ndvi"),
        ("MNDWI", "before_mean_mndwi", "after_mean_mndwi"),
        ("NDBI", "before_mean_ndbi", "after_mean_ndbi"),
    ]
    values = _paired_values(result, mapping, "Index", "Value")
    return grouped_bar_chart(values, "Index", ["NDVI", "MNDWI", "NDBI"], "Value", "Mean spectral index")


def trend_composition_chart(trend_data):
    """
    Independent per-date land-cover composition trend chart.

    Each date is analyzed independently (see methodology_note).
    Points are shown at full opacity when the date's coverage met
    the reliability threshold, and faded when it did not, so a low-
    support date does not visually imply the same confidence as a
    well-supported one.
    """

    chart_rows = []

    for period in trend_data["periods"]:
        for class_name, field in [
            ("Vegetation", "vegetation_percent_of_valid_area"),
            ("Built-up", "built_percent_of_valid_area"),
            ("Water", "water_percent_of_valid_area"),
            ("Bare", "bare_percent_of_valid_area"),
        ]:
            chart_rows.append(
                {
                    "Date": period["date"],
                    "Class": class_name,
                    "Percent": period[field],
                    "Reliable": period["reliable"],
                }
            )

    base = alt.Chart(alt.Data(values=chart_rows)).encode(
        x=alt.X("Date:T", title=None),
        y=alt.Y("Percent:Q", title="Percent of that date's own valid area"),
        color=alt.Color(
            "Class:N",
            legend=alt.Legend(orient="top", title=None),
        ),
    )

    line = base.mark_line()

    points = base.mark_circle(size=90).encode(
        opacity=alt.condition(
            "datum.Reliable == true",
            alt.value(1.0),
            alt.value(0.25),
        ),
        tooltip=[
            alt.Tooltip("Date:T"),
            alt.Tooltip("Class:N"),
            alt.Tooltip("Percent:Q", format=".1f"),
            alt.Tooltip("Reliable:N"),
        ],
    )

    return (
        (line + points)
        .properties(height=320)
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#8a9095",
            titleColor="#8a9095",
            gridColor="#222629",
            domainColor="#303438",
            tickColor="#303438",
        )
        .configure_legend(labelColor="#a4a9ae")
    )


# ==========================================================
# AI QUERY RESOLUTION
# ==========================================================

def resolve_ai_answer(mode, question, result, location, before, after):
    """
    Answer a question using Gemini, falling back to local
    measurement-based answers if the LLM is unavailable.

    Returns (answer, source, status_message).
    """
    if mode == "historical_spectral":
        gemini_fn, fallback_fn = ask_gemini_historical, answer_historical_query
        primary_source, fallback_source = "gemini-historical", "historical-local"
    else:
        gemini_fn, fallback_fn = ask_gemini, answer_query
        primary_source, fallback_source = "gemini", "fallback"

    try:
        answer = gemini_fn(question=question, result=result, location=location, before_date=before, after_date=after)
        return answer, primary_source, None
    except (LLMUnavailableError, LLMConfigurationError) as error:
        return fallback_fn(question, result), fallback_source, str(error)
    except Exception as error:
        return fallback_fn(question, result), fallback_source, f"AI service error: {error}"


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

    # ------------------------------------------------------
    # ANALYSIS TYPE
    # ------------------------------------------------------

    analysis_type = st.selectbox(
        "Analysis type",
        options=[
            "Compare two dates",
            "View trend over time",
        ],
        index=0,
        help=(
            "Compare two dates measures change between a Before "
            "and After period. Trend mode measures land-cover "
            "composition independently at several dates."
        ),
    )

    # ------------------------------------------------------
    # LOCATION
    # ------------------------------------------------------

    location_name = st.text_input(
        "Location",
        placeholder="Powai Lake, Mumbai",
        help="Search for a city, locality, landmark, campus, lake, village, or another named place.",
    )

    if st.button("Find location", use_container_width=True):
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
        selected_location = st.session_state.selected_location

        st.caption(
            f"Selected center · {selected_location['latitude']:.5f}, "
            f"{selected_location['longitude']:.5f}"
        )

    # ------------------------------------------------------
    # DATES
    # ------------------------------------------------------

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

            default_date = (
                today
                - timedelta(
                    days=(
                        (trend_point_count - 1 - point_index)
                        * 365
                    )
                )
            )

            if default_date < TREND_MIN_DATE:
                default_date = TREND_MIN_DATE + timedelta(
                    days=point_index * 30
                )

            picked_date = st.date_input(
                f"Date {point_index + 1}",
                value=default_date,
                min_value=TREND_MIN_DATE,
                max_value=today,
                key=f"trend_date_{point_index}",
            )

            trend_dates.append(picked_date)

    # ------------------------------------------------------
    # RADIUS
    # ------------------------------------------------------

    radius_km = st.slider(
        "Radius",
        min_value=RADIUS_MIN_KM,
        max_value=RADIUS_MAX_KM,
        value=RADIUS_DEFAULT_KM,
        format="%d km",
    )
    st.caption("Circular study area around the selected center.")

    # ------------------------------------------------------
    # MODE
    # ------------------------------------------------------

    if analysis_type == "Compare two dates":
        predicted_mode = choose_analysis_mode(before_date, after_date)
        st.caption("Sentinel-2 + Dynamic World" if predicted_mode == "modern_ml" else "Landsat historical analysis")
    else:
        st.caption("Sentinel-2 + Dynamic World · independent per-date analysis")

    # ------------------------------------------------------
    # ANALYZE
    # ------------------------------------------------------

    run_clicked = st.button(
        "Analyze",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.selected_location is None,
    )

    if (
        st.session_state.analysis_data is not None
        or st.session_state.trend_data is not None
    ):
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

    selected_location = (
        st.session_state.selected_location
    )

    if selected_location is None:

        st.error(
            "Find and select a location before analyzing."
        )

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
            print(
                f"SetQuery Earth Engine analysis: "
                f"{elapsed:.1f} seconds"
            )

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
                    dates=[
                        str(single_date)
                        for single_date in trend_dates
                    ],
                    radius_km=radius_km,
                    confidence_threshold=CONFIDENCE_THRESHOLD,
                )

            elapsed = time.perf_counter() - start_time
            print(
                f"SetQuery Earth Engine trend analysis: "
                f"{elapsed:.1f} seconds"
            )

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

    st.markdown(
        '<div class="sq-workspace-spacer"></div>',
        unsafe_allow_html=True,
    )

    st.title(
        "Satellite change analysis"
    )

    if (
        st.session_state.selected_location
        is None
    ):

        st.write(
            "Search for a location in the sidebar, "
            "choose the correct match, and set the "
            "analysis period and radius."
        )

        st.caption(
            "Sentinel-2 · Dynamic World · Landsat"
        )

    else:

        selected_location = (
            st.session_state.selected_location
        )

        st.write(
            "The analysis center is selected. "
            "Set the dates and radius, then run the analysis."
        )

        st.caption(
            selected_location[
                "address"
            ]
        )

        study_map = build_study_area_map(
            latitude=(
                selected_location[
                    "latitude"
                ]
            ),
            longitude=(
                selected_location[
                    "longitude"
                ]
            ),
            radius_km=radius_km,
            location_label=(
                selected_location[
                    "address"
                ]
            ),
        )

        st_folium(
            study_map,
            height=480,
            use_container_width=True,
            returned_objects=[],
            key="study_area_map",
        )

        st.caption(
            "Geographic context only · the outlined circle "
            "is the current study area. Satellite analysis "
            "uses Sentinel-2 or Landsat through Earth Engine."
        )

        st.caption(
            "Sentinel-2 · Dynamic World · Landsat"
        )

    st.stop()


# ==========================================================
# TREND RESULT VIEW
# ==========================================================

if trend_data is not None:

    period_dates = [
        period["date"]
        for period in trend_data["periods"]
    ]

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

    section(
        "Study area",
        "Geographic context",
        (
            "Interactive reference map showing the selected "
            "analysis center and circular study area."
        ),
    )

    trend_map = build_study_area_map(
        latitude=trend_data["latitude"],
        longitude=trend_data["longitude"],
        radius_km=trend_data["radius_km"],
        location_label=trend_data["location"],
    )

    st_folium(
        trend_map,
        height=420,
        use_container_width=True,
        returned_objects=[],
        key="trend_study_area_map",
    )

    st.caption(
        "Basemap detail is for geographic context only. "
        "SetQuery measurements use Sentinel-2 and Dynamic World."
    )

    st.divider()

    section(
        "Results",
        "Land-cover trend",
        trend_data["methodology_note"],
    )

    st.info(
        "Each date below is analyzed independently. Faded "
        "points had low comparable coverage for that specific "
        "date and should be interpreted with caution rather "
        "than treated as confirmed measurements."
    )

    st.altair_chart(
        trend_composition_chart(trend_data),
        width="stretch",
    )

    st.caption(
        "Percent values are relative to each date's own valid "
        "area, not the full study area, because coverage can "
        "differ significantly between independently analyzed "
        "dates."
    )

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

    st.dataframe(
        table_rows,
        width="stretch",
        hide_index=True,
    )

    # ------------------------------------------------------
    # ASK SETQUERY (POPOVER)
    # ------------------------------------------------------

    st.divider()
    section("Query", "Ask SetQuery AI")

    with st.popover("Ask SetQuery AI", use_container_width=False):
        st.caption(
            "Ask SetQuery is not yet available for trend "
            "results in this version. Use Compare two dates "
            "to ask grounded questions about a specific "
            "before/after change."
        )

    # ------------------------------------------------------
    # WARNINGS
    # ------------------------------------------------------

    if trend_data.get("warnings"):
        st.divider()
        section("Notes", "Warnings")
        for warning in trend_data["warnings"]:
            st.warning(warning)

    st.divider()

    with st.expander("Methodology and metadata"):

        st.write(f"Total study area: `{trend_data['total_area_km2']:.2f} km²`")
        st.write(f"Classification method: `{trend_data['classification_method']}`")
        st.write(
            "Per-observation probability: "
            f"`≥ {trend_data['confidence_threshold'] * 100:.0f}%`"
        )
        st.write(
            "Minimum confident observations: "
            f"`{trend_data['min_confident_observations']}`"
        )
        st.write(
            "Minimum confidence frequency: "
            f"`≥ {trend_data['min_confidence_frequency'] * 100:.0f}%`"
        )
        st.write(
            "Dominant-class agreement: "
            f"`≥ {trend_data['min_temporal_consensus'] * 100:.0f}%`"
        )
        st.write(
            "Reliable coverage threshold: "
            f"`≥ {trend_data['reliable_coverage_threshold']:.0f}%`"
        )

        st.markdown(
            """
Trend points are independent snapshots, not pairwise
change measurements. No transition classes (e.g.
Vegetation → Built) are calculated in this view. For
pairwise transition analysis, use Compare two dates.

Ask SetQuery is not yet available for trend results in
this version.
"""
        )

    st.markdown(
        '<div class="sq-footer">SetQuery · Satellite change analysis</div>',
        unsafe_allow_html=True,
    )

    st.stop()

# ==========================================================
# COMMON RESULT DATA
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


# ==========================================================
# RESULT HEADER
# ==========================================================

st.markdown(
    '<div class="sq-result-header">'
    f'<div class="sq-location">{location}</div>'
    f'<div class="sq-meta">{before} → {after} &nbsp;·&nbsp; {radius} km radius</div>'
    f'<div class="sq-result-context">{data["mode_label"]} &nbsp;·&nbsp; '
    f'~{data["approximate_resolution_m"]} m</div>'
    '</div>',
    unsafe_allow_html=True,
)


# ==========================================================
# RESULT STUDY AREA MAP
# ==========================================================

section(
    "Study area",
    "Geographic context",
    (
        "Interactive reference map showing the selected "
        "analysis center and circular study area."
    ),
)

result_study_map = build_study_area_map(
    latitude=latitude,
    longitude=longitude,
    radius_km=radius,
    location_label=location,
)

st_folium(
    result_study_map,
    height=420,
    use_container_width=True,
    returned_objects=[],
    key="result_study_area_map",
)

st.caption(
    "Basemap detail is for geographic context only. "
    "SetQuery measurements use the satellite datasets "
    "listed in the analysis methodology."
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

    # ------------------------------------------------------
    # CHANGE MAP
    # ------------------------------------------------------

    section(
        "Imagery",
        "Change map",
        "Dynamic World transitions over the after-period Sentinel-2 composite.",
    )

    change_tab, before_tab, after_tab, compare_tab, burn_tab, veg_tab, flood_tab = st.tabs(
        ["Change map", "Before", "After", "Compare", "Burn evidence", "Vegetation stress", "Flood evidence"]
    )

    with change_tab:
        st.image(data["change_map"]["change_url"], width="stretch")
        render_legend(CHANGE_LEGEND)
        st.caption(
            "Displayed change pixels may be enlarged for visibility. "
            "Area statistics use the original pixels."
        )

    render_before_after_compare(
        (before_tab, after_tab, compare_tab),
        before_url=images["before_url"],
        after_url=images["after_url"],
        before_caption=f"{images['before_sentinel_observations']} Sentinel-2 observations · target {before}",
        after_caption=f"{images['after_sentinel_observations']} Sentinel-2 observations · target {after}",
        before=before,
        after=after,
    )

    with burn_tab:

        burn_evidence = data.get("burn_evidence")

        if burn_evidence is None:

            st.info(
                "Burn evidence is not calculated automatically because "
                "it uses additional spectral analysis and adds noticeable "
                "extra time. Click below to check this specific area and "
                "date range."
            )

            check_burn_clicked = st.button(
                "Check burn evidence (NBR/dNBR, ~5-10s)",
                key="check_burn_evidence_button",
            )

            if check_burn_clicked:

                try:
                    from burn_analysis import analyze_burn_evidence
                    with st.spinner("Calculating burn evidence..."):
                        burn_start_time = time.perf_counter()
                        burn_evidence = analyze_burn_evidence(
                            latitude=latitude,
                            longitude=longitude,
                            before_date=before,
                            after_date=after,
                            radius_km=radius,
                        )
                        burn_elapsed = time.perf_counter() - burn_start_time

                    print(
                        f"SetQuery burn evidence analysis: "
                        f"{burn_elapsed:.1f} seconds"
                    )

                    st.session_state.burn_evidence_data = burn_evidence
                    st.session_state.burn_evidence_error = None
                    st.rerun()

                except Exception as error:
                    st.session_state.burn_evidence_error = (
                        f"Burn evidence could not be calculated: {error}"
                    )
                    st.rerun()

        else:
            burn_evidence = st.session_state.get("burn_evidence_data")

        if burn_evidence:

            st.caption(
                "Spectral evidence from NBR/dNBR, not a "
                "validated fire detection or damage "
                "assessment."
            )

            metric_grid(
                [
                    ("Before mean NBR", f"{burn_evidence['before_mean_nbr']:.3f}"),
                    ("After mean NBR", f"{burn_evidence['after_mean_nbr']:.3f}"),
                    ("Mean dNBR", f"{burn_evidence['mean_dnbr']:+.3f}"),
                ],
                per_row=3,
            )

            severity_rows = [
                {
                    "Category": label.replace("_", " ").title(),
                    "Area": area_km2,
                }
                for label, area_km2 in burn_evidence["severity_area_km2"].items()
            ]

            severity_chart = (
                alt.Chart(alt.Data(values=severity_rows))
                .mark_bar(cornerRadiusTopLeft=1, cornerRadiusTopRight=1)
                .encode(
                    x=alt.X("Category:N", title=None, sort=None),
                    y=alt.Y("Area:Q", title="Area (km²)"),
                    tooltip=[
                        alt.Tooltip("Category:N"),
                        alt.Tooltip("Area:Q", format=".4f"),
                    ],
                )
                .properties(height=250)
                .configure_view(strokeOpacity=0)
                .configure_axis(
                    labelColor="#8a9095",
                    titleColor="#8a9095",
                    gridColor="#222629",
                    domainColor="#303438",
                    tickColor="#303438",
                )
            )

            st.altair_chart(severity_chart, width="stretch")

            st.caption(burn_evidence["severity_thresholds_note"])

            for warning in burn_evidence.get("warnings", []):
                st.warning(warning)

    with veg_tab:

        vegetation_stress = data.get("vegetation_stress")

        if vegetation_stress is None:

            st.info(
                "Vegetation stress is not calculated automatically because "
                "it uses additional spectral analysis and adds noticeable "
                "extra time. Click below to check this specific area and "
                "date range."
            )

            check_veg_clicked = st.button(
                "Check vegetation stress (NDVI change, ~5-10s)",
                key="check_vegetation_stress_button",
            )

            if check_veg_clicked:

                try:
                    from vegetation_stress_analysis import analyze_vegetation_stress
                    with st.spinner("Calculating vegetation stress..."):
                        veg_start_time = time.perf_counter()
                        vegetation_stress = analyze_vegetation_stress(
                            latitude=latitude,
                            longitude=longitude,
                            before_date=before,
                            after_date=after,
                            radius_km=radius,
                        )
                        veg_elapsed = time.perf_counter() - veg_start_time

                    print(
                        f"SetQuery vegetation stress analysis: "
                        f"{veg_elapsed:.1f} seconds"
                    )

                    st.session_state.vegetation_stress_data = vegetation_stress
                    st.session_state.vegetation_stress_error = None
                    st.rerun()

                except Exception as error:
                    st.session_state.vegetation_stress_error = (
                        f"Vegetation stress could not be calculated: {error}"
                    )
                    st.rerun()

        else:
            vegetation_stress = st.session_state.get("vegetation_stress_data")

        if vegetation_stress:

            st.caption(
                "Spectral evidence from NDVI change, not a "
                "validated drought or crop-stress confirmation."
            )

            metric_grid(
                [
                    ("Before mean NDVI", f"{vegetation_stress['before_mean_ndvi']:.3f}"),
                    ("After mean NDVI", f"{vegetation_stress['after_mean_ndvi']:.3f}"),
                    ("Mean NDVI change", f"{vegetation_stress['mean_ndvi_change']:+.3f}"),
                ],
                per_row=3,
            )

            breakdown_rows = [
                {"Category": "Increased", "Percent": vegetation_stress["increased_percent"]},
                {"Category": "Decreased", "Percent": vegetation_stress["decreased_percent"]},
                {"Category": "Stable", "Percent": vegetation_stress["stable_percent"]},
            ]

            breakdown_chart = (
                alt.Chart(alt.Data(values=breakdown_rows))
                .mark_bar(cornerRadiusTopLeft=1, cornerRadiusTopRight=1)
                .encode(
                    x=alt.X("Category:N", title=None, sort=None),
                    y=alt.Y("Percent:Q", title="% of valid area"),
                    tooltip=[
                        alt.Tooltip("Category:N"),
                        alt.Tooltip("Percent:Q", format=".2f"),
                    ],
                )
                .properties(height=250)
                .configure_view(strokeOpacity=0)
                .configure_axis(
                    labelColor="#8a9095",
                    titleColor="#8a9095",
                    gridColor="#222629",
                    domainColor="#303438",
                    tickColor="#303438",
                )
            )

            st.altair_chart(breakdown_chart, width="stretch")

            for warning in vegetation_stress.get("warnings", []):
                st.warning(warning)

    with flood_tab:

        st.caption(
            "SAR-based surface-water change indicator, not a "
            "validated flood damage assessment."
        )

        flood_result = st.session_state.flood_evidence_data
        flood_error = st.session_state.flood_evidence_error

        if flood_result is None:

            st.info(
                "Flood evidence is not calculated automatically because "
                "it uses a separate Sentinel-1 SAR dataset and adds "
                "noticeable extra time. Click below to check this "
                "specific area and date range."
            )

            if flood_error:
                st.warning(flood_error)

            check_flood_clicked = st.button(
                "Check flood evidence (Sentinel-1 SAR, ~10-20s)",
                key="check_flood_evidence_button",
            )

            if check_flood_clicked:

                try:
                    with st.spinner("Running Sentinel-1 SAR flood analysis..."):
                        flood_start_time = time.perf_counter()
                        flood_result = analyze_flood_evidence(
                            latitude=latitude,
                            longitude=longitude,
                            before_date=before,
                            after_date=after,
                            radius_km=radius,
                        )
                        flood_elapsed = time.perf_counter() - flood_start_time

                    print(
                        f"SetQuery flood evidence analysis: "
                        f"{flood_elapsed:.1f} seconds"
                    )

                    st.session_state.flood_evidence_data = flood_result
                    st.session_state.flood_evidence_error = None
                    st.rerun()

                except (FloodValidationError, FloodDataError) as error:
                    st.session_state.flood_evidence_error = str(error)
                    st.rerun()

                except Exception as error:
                    st.session_state.flood_evidence_error = (
                        f"Flood evidence could not be calculated: {error}"
                    )
                    st.rerun()

        else:

            if not flood_result["orbit_matched"]:
                st.warning(
                    "No shared Sentinel-1 orbit pass was found between "
                    "the Before and After periods. This result may be "
                    "affected by viewing-geometry differences."
                )

            metric_grid(
                [
                    ("Before mean VV", f"{flood_result['before_mean_vv_db']:.2f} dB"),
                    ("After mean VV", f"{flood_result['after_mean_vv_db']:.2f} dB"),
                    ("New water", f"{flood_result['new_water_percent_of_valid_area']:.2f}%"),
                ],
                per_row=3,
            )

            st.write(
                f"New water area: `{flood_result['new_water_area_km2']:.3f} km²` "
                f"of `{flood_result['valid_area_km2']:.2f} km²` analyzed"
            )

            for warning in flood_result["warnings"]:
                st.warning(warning)

    # ------------------------------------------------------
    # LAND COVER
    # ------------------------------------------------------

    st.divider()
    section(
        "Results",
        "Land cover",
        "Measurements refer only to pixels that passed the temporal-consensus "
        "requirements in both periods.",
    )

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

    # ------------------------------------------------------
    # TRANSITIONS
    # ------------------------------------------------------

    st.divider()
    section(
        "Details",
        "Transitions",
        "Explicit class transitions are different from net land-cover differences.",
    )

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

    summary = generate_analysis_summary(
        location=location, before_date=before, after_date=after, result=result
    )


# ==========================================================
# HISTORICAL RESULTS
# ==========================================================

else:

    coverage = result["coverage_percent"]
    coverage_level = get_historical_coverage_level(coverage)
    source_support = get_historical_source_support(result)

    render_status(
        f"{coverage_level} spatial coverage · {coverage:.1f}% comparable. "
        "Historical results are spectral-index measurements, not categorical "
        "land-cover area estimates.",
        coverage_level,
    )

    # ------------------------------------------------------
    # SOURCE SUPPORT
    # ------------------------------------------------------

    section(
        "Data",
        "Source support",
        "Coverage describes valid spatial comparison. Source support describes "
        "the number of Landsat observations.",
    )

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

    # ------------------------------------------------------
    # HISTORICAL IMAGERY
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # SPECTRAL RESULTS
    # ------------------------------------------------------

    st.divider()
    section(
        "Results",
        "Spectral comparison",
        "NDVI is vegetation-related, MNDWI is water-related, and NDBI is built/bare-related.",
    )

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

    summary = generate_historical_summary(
        location=location, before_date=before, after_date=after, result=result
    )


# ==========================================================
# ANALYSIS SUMMARY
# ==========================================================

st.divider()
section("Summary", "Analysis")
st.write(summary)


# ==========================================================
# ASK SETQUERY (POPOVER)
# ==========================================================

st.divider()
section("Query", "Ask SetQuery AI", "Ask a question about the current analysis.")

with st.popover("Ask SetQuery AI", use_container_width=False):

    with st.form("question_form", clear_on_submit=False):
        question = st.text_input(
            "Question",
            placeholder="What changed in this area?",
            label_visibility="collapsed",
        )
        ask_clicked = st.form_submit_button(
            "Ask",
            type="primary",
            use_container_width=True,
        )

    if ask_clicked and question.strip():
        answer, source, status = resolve_ai_answer(
            mode, question, result, location, before, after
        )
        st.session_state.ai_answer = answer
        st.session_state.ai_source = source
        st.session_state.ai_status = status

    if st.session_state.ai_answer:

        st.divider()

        st.caption(
            AI_SOURCE_CAPTIONS.get(
                st.session_state.ai_source,
                "Local response from analysis measurements",
            )
        )
        st.write(st.session_state.ai_answer)

        if st.session_state.ai_status:
            with st.expander("Service status"):
                st.caption(st.session_state.ai_status)


# ==========================================================
# PROCESS QUESTION
# ==========================================================

if ask_clicked and question.strip():
    answer, source, status = resolve_ai_answer(mode, question, result, location, before, after)
    st.session_state.ai_answer = answer
    st.session_state.ai_source = source
    st.session_state.ai_status = status


# ==========================================================
# RESPONSE
# ==========================================================

if st.session_state.ai_answer:

    st.caption(AI_SOURCE_CAPTIONS.get(st.session_state.ai_source, "Local response from analysis measurements"))
    st.write(st.session_state.ai_answer)

    if st.session_state.ai_status:
        with st.expander("Service status"):
            st.caption(st.session_state.ai_status)


# ==========================================================
# METHODOLOGY / METADATA
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
        st.write(f"Minimum confidence frequency: `≥ {result.get('min_confidence_frequency', 0.50) * 100:.0f}%`")
        st.write(f"Dominant-class agreement: `≥ {result.get('min_temporal_consensus', 0.60) * 100:.0f}%`")
        st.write(
            f"Dynamic World observations: `{result['before_observations']} / {result['after_observations']}`"
        )
        st.write(
            "Sentinel-2 observations: "
            f"`{images['before_sentinel_observations']} / {images['after_sentinel_observations']}`"
        )
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

Named-place search determines the center of the circular
study area. It does not use the exact administrative,
campus, parcel, lake, or property boundary of the named
location.

The application is intended for area-level analysis and
should not be used to claim exact property-level changes
or exact causes of observed differences.
"""
    )


# ==========================================================
# FOOTER
# ==========================================================

st.markdown('<div class="sq-footer">SetQuery · Satellite change analysis</div>', unsafe_allow_html=True)