from datetime import date
from pathlib import Path
import time

import altair as alt
import requests 
import streamlit as st
from geopy.geocoders import Nominatim

from analysis import AnalysisValidationError, AnalysisDataError
from historical_analysis import HistoricalValidationError, HistoricalDataError
from analysis_router import run_routed_analysis, choose_analysis_mode
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

    before_date = st.date_input("Before", value=date(2022, 9, 15))
    after_date = st.date_input("After", value=date(2025, 9, 15))

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

    predicted_mode = choose_analysis_mode(before_date, after_date)
    st.caption("Sentinel-2 + Dynamic World" if predicted_mode == "modern_ml" else "Landsat historical analysis")

    # ------------------------------------------------------
    # ANALYZE
    # ------------------------------------------------------

    run_clicked = st.button(
        "Analyze",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.selected_location is None,
    )

    if st.session_state.analysis_data is not None:
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

    else:

        try:

            with st.spinner(
                "Analyzing satellite data..."
            ):

                routed = run_routed_analysis(
                    latitude=selected_location["latitude"],
                    longitude=selected_location["longitude"],
                    before_date=str(before_date),
                    after_date=str(after_date),
                    radius_km=radius_km,
                    confidence_threshold=CONFIDENCE_THRESHOLD,
                )

                previews = prepare_preview_images(
                    routed
                )

                st.session_state.analysis_data = {
                    "location":
                        selected_location["address"],

                    "latitude":
                        selected_location["latitude"],

                    "longitude":
                        selected_location["longitude"],

                    "radius_km":
                        radius_km,

                    "before_date":
                        str(before_date),

                    "after_date":
                        str(after_date),

                    "previews":
                        previews,

                    **routed,
                }

        except (
            AnalysisValidationError,
            HistoricalValidationError,
            AnalysisDataError,
            HistoricalDataError,
            ValueError,
        ) as error:

            st.error(
                str(error)
            )

        except Exception as error:

            st.error(
                "Analysis could not be completed."
            )

            with st.expander(
                "Technical details"
            ):

                st.exception(
                    error
                )


# ==========================================================
# ACTIVE ANALYSIS
# ==========================================================

data = st.session_state.analysis_data


# ==========================================================
# EMPTY WORKSPACE
# ==========================================================

if data is None:

    st.markdown('<div class="sq-workspace-spacer"></div>', unsafe_allow_html=True)
    st.title("Satellite change analysis")

    if st.session_state.selected_location is None:
        st.write(
            "Search for a location in the sidebar, choose the correct match, "
            "and set the analysis period and radius."
        )
    else:
        st.write("The analysis center is selected. Set the dates and radius, then run the analysis.")
        st.caption(st.session_state.selected_location["address"])

    st.caption("Sentinel-2 · Dynamic World · Landsat")
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

    change_tab, before_tab, after_tab, compare_tab = st.tabs(["Change map", "Before", "After", "Compare"])

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
# ASK SETQUERY
# ==========================================================

st.divider()
section("Query", "Ask SetQuery", "Ask a question about the current analysis.")

with st.form("question_form", clear_on_submit=False):
    question = st.text_input(
        "Question",
        placeholder="What changed in this area?",
        label_visibility="collapsed",
    )
    ask_clicked = st.form_submit_button("Ask", type="primary", use_container_width=False)


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