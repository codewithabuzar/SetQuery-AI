from datetime import date
from pathlib import Path

import altair as alt
import streamlit as st
from geopy.geocoders import Nominatim

from analysis import (
    AnalysisValidationError,
    AnalysisDataError,
)
from historical_analysis import (
    HistoricalValidationError,
    HistoricalDataError,
)
from analysis_router import (
    run_routed_analysis,
    choose_analysis_mode,
)
from report import (
    generate_analysis_summary,
    get_coverage_interpretation,
)
from historical_report import (
    generate_historical_summary,
    get_historical_coverage_level,
    get_historical_source_support,
    get_historical_support_warnings,
    answer_historical_query,
)
from query import answer_query
from llm import (
    ask_gemini,
    ask_gemini_historical,
    LLMUnavailableError,
    LLMConfigurationError,
)


# ==========================================================
# CONFIGURATION
# ==========================================================

CONFIDENCE_THRESHOLD = 0.60

RADIUS_MIN_KM = 1
RADIUS_MAX_KM = 20
RADIUS_DEFAULT_KM = 10


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

STYLE_PATH = (
    Path(__file__).parent
    / "assets"
    / "style.css"
)

if STYLE_PATH.exists():

    css = STYLE_PATH.read_text(
        encoding="utf-8"
    )

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )


# ==========================================================
# UI HELPERS
# ==========================================================

def section(
    label,
    title,
    description=None,
):
    """Render a minimal section heading."""

    if label:

        st.markdown(
            (
                '<div class="sq-section-label">'
                f"{label}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    st.subheader(
        title
    )

    if description:

        st.caption(
            description
        )


def sensor_text(
    sensor_list,
):
    """Format Landsat sensor metadata."""

    if not sensor_list:

        return "No sensor metadata"

    return ", ".join(
        (
            f"{item['name']} "
            f"({item['observations']} obs.)"
        )
        for item in sensor_list
    )


def coverage_status_class(
    level,
):
    """Select status style from coverage category."""

    if level == "GOOD":

        return "sq-status-good"

    if level in (
        "MODERATE",
        "LIMITED",
    ):

        return "sq-status-warning"

    return "sq-status-danger"


def render_status(
    text,
    level,
):
    """Render restrained analysis-quality status."""

    css_class = (
        coverage_status_class(
            level
        )
    )

    st.markdown(
        (
            f'<div class="sq-status {css_class}">'
            f"{text}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def open_workspace():
    """Open the analysis workspace."""

    st.session_state.app_view = (
        "workspace"
    )


def open_home():
    """Return to the landing page."""

    st.session_state.app_view = (
        "home"
    )


def clear_analysis():
    """Clear the current analysis and question state."""

    st.session_state.analysis_data = (
        None
    )

    st.session_state.ai_answer = (
        None
    )

    st.session_state.ai_source = (
        None
    )

    st.session_state.ai_status = (
        None
    )


# ==========================================================
# CHARTS
# ==========================================================

def modern_land_cover_chart(
    result,
):
    """Before/After land-cover chart."""

    values = [
        {
            "Class": "Vegetation",
            "Period": "Before",
            "Area": result[
                "before_vegetation_km2"
            ],
        },
        {
            "Class": "Vegetation",
            "Period": "After",
            "Area": result[
                "after_vegetation_km2"
            ],
        },
        {
            "Class": "Built-up",
            "Period": "Before",
            "Area": result[
                "before_built_km2"
            ],
        },
        {
            "Class": "Built-up",
            "Period": "After",
            "Area": result[
                "after_built_km2"
            ],
        },
        {
            "Class": "Water",
            "Period": "Before",
            "Area": result[
                "before_water_km2"
            ],
        },
        {
            "Class": "Water",
            "Period": "After",
            "Area": result[
                "after_water_km2"
            ],
        },
        {
            "Class": "Bare",
            "Period": "Before",
            "Area": result[
                "before_bare_km2"
            ],
        },
        {
            "Class": "Bare",
            "Period": "After",
            "Area": result[
                "after_bare_km2"
            ],
        },
    ]

    return (
        alt.Chart(
            alt.Data(
                values=values
            )
        )
        .mark_bar(
            cornerRadiusTopLeft=1,
            cornerRadiusTopRight=1,
        )
        .encode(
            x=alt.X(
                "Class:N",
                title=None,
                sort=[
                    "Vegetation",
                    "Built-up",
                    "Water",
                    "Bare",
                ],
            ),

            xOffset=alt.XOffset(
                "Period:N"
            ),

            y=alt.Y(
                "Area:Q",
                title="Area (km²)",
            ),

            color=alt.Color(
                "Period:N",

                scale=alt.Scale(
                    domain=[
                        "Before",
                        "After",
                    ],

                    range=[
                        "#696e72",
                        "#d9dddf",
                    ],
                ),

                legend=alt.Legend(
                    orient="top",
                    title=None,
                ),
            ),

            tooltip=[
                alt.Tooltip(
                    "Class:N",
                ),

                alt.Tooltip(
                    "Period:N",
                ),

                alt.Tooltip(
                    "Area:Q",
                    title="Area (km²)",
                    format=".3f",
                ),
            ],
        )
        .properties(
            height=250
        )
        .configure_view(
            strokeOpacity=0
        )
        .configure_axis(
            labelColor="#8a9095",
            titleColor="#8a9095",
            gridColor="#222629",
            domainColor="#303438",
            tickColor="#303438",
        )
        .configure_legend(
            labelColor="#a4a9ae"
        )
    )


def historical_index_chart(
    result,
):
    """Before/After historical spectral-index chart."""

    values = [
        {
            "Index": "NDVI",
            "Period": "Before",
            "Value": result[
                "before_mean_ndvi"
            ],
        },
        {
            "Index": "NDVI",
            "Period": "After",
            "Value": result[
                "after_mean_ndvi"
            ],
        },
        {
            "Index": "MNDWI",
            "Period": "Before",
            "Value": result[
                "before_mean_mndwi"
            ],
        },
        {
            "Index": "MNDWI",
            "Period": "After",
            "Value": result[
                "after_mean_mndwi"
            ],
        },
        {
            "Index": "NDBI",
            "Period": "Before",
            "Value": result[
                "before_mean_ndbi"
            ],
        },
        {
            "Index": "NDBI",
            "Period": "After",
            "Value": result[
                "after_mean_ndbi"
            ],
        },
    ]

    return (
        alt.Chart(
            alt.Data(
                values=values
            )
        )
        .mark_bar(
            cornerRadiusTopLeft=1,
            cornerRadiusTopRight=1,
        )
        .encode(
            x=alt.X(
                "Index:N",
                title=None,
                sort=[
                    "NDVI",
                    "MNDWI",
                    "NDBI",
                ],
            ),

            xOffset=alt.XOffset(
                "Period:N"
            ),

            y=alt.Y(
                "Value:Q",
                title="Mean spectral index",
            ),

            color=alt.Color(
                "Period:N",

                scale=alt.Scale(
                    domain=[
                        "Before",
                        "After",
                    ],

                    range=[
                        "#696e72",
                        "#d9dddf",
                    ],
                ),

                legend=alt.Legend(
                    orient="top",
                    title=None,
                ),
            ),

            tooltip=[
                alt.Tooltip(
                    "Index:N",
                ),

                alt.Tooltip(
                    "Period:N",
                ),

                alt.Tooltip(
                    "Value:Q",
                    format=".3f",
                ),
            ],
        )
        .properties(
            height=250
        )
        .configure_view(
            strokeOpacity=0
        )
        .configure_axis(
            labelColor="#8a9095",
            titleColor="#8a9095",
            gridColor="#222629",
            domainColor="#303438",
            tickColor="#303438",
        )
        .configure_legend(
            labelColor="#a4a9ae"
        )
    )


# ==========================================================
# SESSION STATE
# ==========================================================

SESSION_DEFAULTS = {
    "app_view": "home",
    "analysis_data": None,
    "ai_answer": None,
    "ai_source": None,
    "ai_status": None,
}


for key, value in (
    SESSION_DEFAULTS.items()
):

    if key not in st.session_state:

        st.session_state[
            key
        ] = value


# ==========================================================
# LANDING PAGE
# ==========================================================

if (
    st.session_state.app_view
    == "home"
):

    st.markdown(
        """
<style>
section[data-testid="stSidebar"] {
    display: none !important;
}

[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

.block-container {
    max-width: 1180px !important;
    padding-top: 5rem !important;
    padding-left: 4rem !important;
    padding-right: 4rem !important;
}
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sq-home-brand">SetQuery</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sq-home-space"></div>',
        unsafe_allow_html=True,
    )

    st.title(
        "Satellite change analysis"
    )

    st.markdown(
        """
Compare a place across time using satellite imagery and
measured land-cover or spectral change.
"""
    )

    st.caption(
        "Sentinel-2 · Dynamic World · Landsat · "
        "Google Earth Engine"
    )

    st.markdown(
        '<div class="sq-home-button-space"></div>',
        unsafe_allow_html=True,
    )

    st.button(
        "Open analysis",
        key="open_analysis",
        type="primary",
        on_click=open_workspace,
    )

    st.stop()


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:

    st.markdown(
        """
<div class="sq-brand">
    <div class="sq-brand-name">
        SetQuery
    </div>
    <div class="sq-brand-sub">
        Satellite change analysis
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            '<div class="sq-sidebar-section">'
            "Analysis"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    location_name = st.text_input(
        "Location",
        placeholder=(
            "Mumbai, Maharashtra, India"
        ),
    )

    before_date = st.date_input(
        "Before",
        value=date(
            2022,
            9,
            15,
        ),
    )

    after_date = st.date_input(
        "After",
        value=date(
            2025,
            9,
            15,
        ),
    )

    radius_km = st.slider(
        "Radius",
        min_value=RADIUS_MIN_KM,
        max_value=RADIUS_MAX_KM,
        value=RADIUS_DEFAULT_KM,
        format="%d km",
    )

    predicted_mode = (
        choose_analysis_mode(
            before_date,
            after_date,
        )
    )

    if (
        predicted_mode
        == "modern_ml"
    ):

        st.caption(
            "Sentinel-2 + Dynamic World"
        )

    else:

        st.caption(
            "Landsat historical analysis"
        )

    run_clicked = st.button(
        "Analyze",
        type="primary",
        use_container_width=True,
    )

    if (
        st.session_state.analysis_data
        is not None
    ):

        st.button(
            "Clear analysis",
            use_container_width=True,
            on_click=clear_analysis,
        )

    st.markdown(
        '<div class="sq-sidebar-rule"></div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Target dates represent composite windows, "
        "not exact acquisition dates."
    )

    st.button(
        "Back to home",
        use_container_width=True,
        on_click=open_home,
    )


# ==========================================================
# RUN ANALYSIS
# ==========================================================

if run_clicked:

    clear_analysis()

    if not location_name.strip():

        st.error(
            "Enter a location."
        )

    else:

        try:

            with st.spinner(
                "Analyzing satellite data..."
            ):

                geocoder = Nominatim(
                    user_agent=(
                        "setquery-ai-student-project"
                    )
                )

                resolved = (
                    geocoder.geocode(
                        location_name,
                        timeout=10,
                    )
                )

                if resolved is None:

                    raise ValueError(
                        "Location not found. "
                        "Try a more specific place name."
                    )

                routed = (
                    run_routed_analysis(
                        latitude=(
                            resolved.latitude
                        ),
                        longitude=(
                            resolved.longitude
                        ),
                        before_date=str(
                            before_date
                        ),
                        after_date=str(
                            after_date
                        ),
                        radius_km=(
                            radius_km
                        ),
                        confidence_threshold=(
                            CONFIDENCE_THRESHOLD
                        ),
                    )
                )

                st.session_state.analysis_data = {
                    "location":
                        resolved.address,

                    "latitude":
                        resolved.latitude,

                    "longitude":
                        resolved.longitude,

                    "radius_km":
                        radius_km,

                    "before_date":
                        str(before_date),

                    "after_date":
                        str(after_date),

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

data = (
    st.session_state.analysis_data
)


# ==========================================================
# EMPTY WORKSPACE
# ==========================================================

if data is None:

    st.markdown(
        '<div class="sq-workspace-spacer"></div>',
        unsafe_allow_html=True,
    )

    st.title(
        "Satellite change analysis"
    )

    st.write(
        "Set a location, two dates, and an analysis "
        "radius in the sidebar to begin."
    )

    st.caption(
        "Sentinel-2 · Dynamic World · Landsat"
    )

    st.stop()

# ==========================================================
# COMMON RESULT DATA
# ==========================================================

mode = data[
    "mode"
]

result = data[
    "result"
]

images = data[
    "images"
]

location = data[
    "location"
]

latitude = data[
    "latitude"
]

longitude = data[
    "longitude"
]

before = data[
    "before_date"
]

after = data[
    "after_date"
]

radius = data[
    "radius_km"
]


# ==========================================================
# RESULT HEADER
# ==========================================================

st.markdown(
    (
        '<div class="sq-result-header">'
        '<div class="sq-location">'
        f"{location}"
        "</div>"
        '<div class="sq-meta">'
        f"{before} → {after}"
        " &nbsp;·&nbsp; "
        f"{radius} km radius"
        "</div>"
        '<div class="sq-result-context">'
        f"{data['mode_label']}"
        " &nbsp;·&nbsp; "
        f"~{data['approximate_resolution_m']} m"
        "</div>"
        "</div>"
    ),
    unsafe_allow_html=True,
)


# ==========================================================
# MODERN RESULTS
# ==========================================================

if mode == "modern_ml":

    coverage = result[
        "coverage_percent"
    ]

    coverage_info = (
        get_coverage_interpretation(
            coverage
        )
    )

    coverage_level = (
        coverage_info[
            "level"
        ]
    )

    render_status(
        (
            f"{coverage_level} coverage · "
            f"{coverage:.1f}% comparable · "
            f"{coverage_info['description']}"
        ),
        coverage_level,
    )

    # ------------------------------------------------------
    # CHANGE MAP
    # ------------------------------------------------------

    section(
        "Imagery",
        "Change map",
        (
            "Dynamic World transitions over the "
            "after-period Sentinel-2 composite."
        ),
    )

    (
        change_tab,
        before_tab,
        after_tab,
        compare_tab,
    ) = st.tabs(
        [
            "Change map",
            "Before",
            "After",
            "Compare",
        ]
    )

    with change_tab:

        st.image(
            data[
                "change_map"
            ][
                "change_url"
            ],
            width="stretch",
        )

        # Strong colors remain here because they encode
        # actual transition classes.
        legend_html = (
            '<div class="sq-legend">'

            '<span class="sq-legend-item">'
            '<span class="sq-dot" '
            'style="background:#ff0000"></span>'
            "Vegetation → Built"
            "</span>"

            '<span class="sq-legend-item">'
            '<span class="sq-dot" '
            'style="background:#00d45a"></span>'
            "Built → Vegetation"
            "</span>"

            '<span class="sq-legend-item">'
            '<span class="sq-dot" '
            'style="background:#e6c800"></span>'
            "Bare → Built"
            "</span>"

            '<span class="sq-legend-item">'
            '<span class="sq-dot" '
            'style="background:#3278ff"></span>'
            "Non-water → Water"
            "</span>"

            '<span class="sq-legend-item">'
            '<span class="sq-dot" '
            'style="background:#e78134"></span>'
            "Water → Non-water"
            "</span>"

            "</div>"
        )

        st.markdown(
            legend_html,
            unsafe_allow_html=True,
        )

        st.caption(
            "Displayed change pixels may be enlarged "
            "for visibility. Area statistics use the "
            "original pixels."
        )

    with before_tab:

        st.image(
            images[
                "before_url"
            ],
            width="stretch",
        )

        st.caption(
            f"{images['before_sentinel_observations']} "
            f"Sentinel-2 observations · target {before}"
        )

    with after_tab:

        st.image(
            images[
                "after_url"
            ],
            width="stretch",
        )

        st.caption(
            f"{images['after_sentinel_observations']} "
            f"Sentinel-2 observations · target {after}"
        )

    with compare_tab:

        compare_before, compare_after = (
            st.columns(2)
        )

        with compare_before:

            st.markdown(
                f"### Before · {before}"
            )

            st.image(
                images[
                    "before_url"
                ],
                width="stretch",
            )

        with compare_after:

            st.markdown(
                f"### After · {after}"
            )

            st.image(
                images[
                    "after_url"
                ],
                width="stretch",
            )

    # ------------------------------------------------------
    # LAND COVER
    # ------------------------------------------------------

    st.divider()

    section(
        "Results",
        "Land cover",
        (
            "Measurements refer only to pixels that "
            "passed the temporal-consensus requirements "
            "in both periods."
        ),
    )

    vegetation_change = (
        result[
            "after_vegetation_km2"
        ]
        -
        result[
            "before_vegetation_km2"
        ]
    )

    built_change = (
        result[
            "after_built_km2"
        ]
        -
        result[
            "before_built_km2"
        ]
    )

    metric1, metric2, metric3, metric4 = (
        st.columns(4)
    )

    metric1.metric(
        "Coverage",
        f"{coverage:.1f}%",
    )

    metric2.metric(
        "Comparable area",
        (
            f"{result['comparable_area_km2']:.2f} km²"
        ),
    )

    metric3.metric(
        "Vegetation",
        (
            f"{vegetation_change:+.3f} km²"
        ),
    )

    metric4.metric(
        "Built-up",
        (
            f"{built_change:+.3f} km²"
        ),
    )

    st.altair_chart(
        modern_land_cover_chart(
            result
        ),
        width="stretch",
    )

    before_values, after_values = (
        st.columns(2)
    )

    with before_values:

        st.markdown(
            f"### Before · {before}"
        )

        bv1, bv2 = (
            st.columns(2)
        )

        bv1.metric(
            "Vegetation",
            (
                f"{result['before_vegetation_km2']:.2f} km²"
            ),
        )

        bv2.metric(
            "Built-up",
            (
                f"{result['before_built_km2']:.2f} km²"
            ),
        )

        bv3, bv4 = (
            st.columns(2)
        )

        bv3.metric(
            "Water",
            (
                f"{result['before_water_km2']:.2f} km²"
            ),
        )

        bv4.metric(
            "Bare",
            (
                f"{result['before_bare_km2']:.2f} km²"
            ),
        )

    with after_values:

        st.markdown(
            f"### After · {after}"
        )

        av1, av2 = (
            st.columns(2)
        )

        av1.metric(
            "Vegetation",
            (
                f"{result['after_vegetation_km2']:.2f} km²"
            ),
        )

        av2.metric(
            "Built-up",
            (
                f"{result['after_built_km2']:.2f} km²"
            ),
        )

        av3, av4 = (
            st.columns(2)
        )

        av3.metric(
            "Water",
            (
                f"{result['after_water_km2']:.2f} km²"
            ),
        )

        av4.metric(
            "Bare",
            (
                f"{result['after_bare_km2']:.2f} km²"
            ),
        )

    # ------------------------------------------------------
    # TRANSITIONS
    # ------------------------------------------------------

    st.divider()

    section(
        "Details",
        "Transitions",
        (
            "Explicit class transitions are different "
            "from net land-cover differences."
        ),
    )

    transition1, transition2, transition3 = (
        st.columns(3)
    )

    transition1.metric(
        "Vegetation → Built",
        (
            f"{result['vegetation_to_built_km2']:.4f} km²"
        ),
    )

    transition2.metric(
        "Built → Vegetation",
        (
            f"{result['built_to_vegetation_km2']:.4f} km²"
        ),
    )

    transition3.metric(
        "Bare → Built",
        (
            f"{result['bare_to_built_km2']:.4f} km²"
        ),
    )

    transition4, transition5 = (
        st.columns(2)
    )

    transition4.metric(
        "Water → Non-water",
        (
            f"{result['water_to_nonwater_km2']:.4f} km²"
        ),
    )

    transition5.metric(
        "Non-water → Water",
        (
            f"{result['nonwater_to_water_km2']:.4f} km²"
        ),
    )

    summary = (
        generate_analysis_summary(
            location=location,
            before_date=before,
            after_date=after,
            result=result,
        )
    )


# ==========================================================
# HISTORICAL RESULTS
# ==========================================================

else:

    coverage = result[
        "coverage_percent"
    ]

    coverage_level = (
        get_historical_coverage_level(
            coverage
        )
    )

    source_support = (
        get_historical_source_support(
            result
        )
    )

    render_status(
        (
            f"{coverage_level} spatial coverage · "
            f"{coverage:.1f}% comparable. "
            "Historical results are spectral-index "
            "measurements, not categorical land-cover "
            "area estimates."
        ),
        coverage_level,
    )

    # ------------------------------------------------------
    # SOURCE SUPPORT
    # ------------------------------------------------------

    section(
        "Data",
        "Source support",
        (
            "Coverage describes valid spatial comparison. "
            "Source support describes the number of "
            "Landsat observations."
        ),
    )

    support1, support2, support3 = (
        st.columns(3)
    )

    support1.metric(
        "Coverage",
        f"{coverage:.1f}%",
    )

    support2.metric(
        "Before support",
        source_support[
            "before_level"
        ],
        (
            f"{source_support['before_count']} obs."
        ),
    )

    support3.metric(
        "After support",
        source_support[
            "after_level"
        ],
        (
            f"{source_support['after_count']} obs."
        ),
    )

    for warning in (
        get_historical_support_warnings(
            result
        )
    ):

        st.warning(
            warning
        )

    # ------------------------------------------------------
    # HISTORICAL IMAGERY
    # ------------------------------------------------------

    st.divider()

    section(
        "Imagery",
        "Landsat comparison",
    )

    (
        historical_before_tab,
        historical_after_tab,
        historical_compare_tab,
    ) = st.tabs(
        [
            "Before",
            "After",
            "Compare",
        ]
    )

    with historical_before_tab:

        st.image(
            images[
                "before_url"
            ],
            width="stretch",
        )

        st.caption(
            sensor_text(
                images[
                    "before_sensors"
                ]
            )
        )

    with historical_after_tab:

        st.image(
            images[
                "after_url"
            ],
            width="stretch",
        )

        st.caption(
            sensor_text(
                images[
                    "after_sensors"
                ]
            )
        )

    with historical_compare_tab:

        historical_before, historical_after = (
            st.columns(2)
        )

        with historical_before:

            st.markdown(
                f"### Before · {before}"
            )

            st.image(
                images[
                    "before_url"
                ],
                width="stretch",
            )

        with historical_after:

            st.markdown(
                f"### After · {after}"
            )

            st.image(
                images[
                    "after_url"
                ],
                width="stretch",
            )

    # ------------------------------------------------------
    # SPECTRAL RESULTS
    # ------------------------------------------------------

    st.divider()

    section(
        "Results",
        "Spectral comparison",
        (
            "NDVI is vegetation-related, MNDWI is "
            "water-related, and NDBI is built/bare-related."
        ),
    )

    index1, index2, index3, index4 = (
        st.columns(4)
    )

    index1.metric(
        "Comparable area",
        (
            f"{result['comparable_area_km2']:.2f} km²"
        ),
    )

    index2.metric(
        "NDVI",
        (
            f"{result['ndvi_change']:+.3f}"
        ),
    )

    index3.metric(
        "MNDWI",
        (
            f"{result['mndwi_change']:+.3f}"
        ),
    )

    index4.metric(
        "NDBI",
        (
            f"{result['ndbi_change']:+.3f}"
        ),
    )

    st.altair_chart(
        historical_index_chart(
            result
        ),
        width="stretch",
    )

    before_indices, after_indices = (
        st.columns(2)
    )

    with before_indices:

        st.markdown(
            f"### Before · {before}"
        )

        st.metric(
            "NDVI",
            (
                f"{result['before_mean_ndvi']:.3f}"
            ),
        )

        st.metric(
            "MNDWI",
            (
                f"{result['before_mean_mndwi']:.3f}"
            ),
        )

        st.metric(
            "NDBI",
            (
                f"{result['before_mean_ndbi']:.3f}"
            ),
        )

    with after_indices:

        st.markdown(
            f"### After · {after}"
        )

        st.metric(
            "NDVI",
            (
                f"{result['after_mean_ndvi']:.3f}"
            ),
        )

        st.metric(
            "MNDWI",
            (
                f"{result['after_mean_mndwi']:.3f}"
            ),
        )

        st.metric(
            "NDBI",
            (
                f"{result['after_mean_ndbi']:.3f}"
            ),
        )

    for warning in result.get(
        "warnings",
        [],
    ):

        st.warning(
            warning
        )

    summary = (
        generate_historical_summary(
            location=location,
            before_date=before,
            after_date=after,
            result=result,
        )
    )


# ==========================================================
# ANALYSIS SUMMARY
# ==========================================================

st.divider()

section(
    "Summary",
    "Analysis",
)

st.write(
    summary
)


# ==========================================================
# ASK SETQUERY
# ==========================================================

st.divider()

section(
    "Query",
    "Ask SetQuery",
    (
        "Ask a question about the current analysis."
    ),
)


with st.form(
    "question_form",
    clear_on_submit=False,
):

    question = st.text_input(
        "Question",
        placeholder=(
            "What changed in this area?"
        ),
        label_visibility="collapsed",
    )

    ask_clicked = (
        st.form_submit_button(
            "Ask",
            type="primary",
            use_container_width=False,
        )
    )


# ==========================================================
# PROCESS QUESTION
# ==========================================================

if (
    ask_clicked
    and question.strip()
):

    if (
        mode
        == "historical_spectral"
    ):

        try:

            answer = (
                ask_gemini_historical(
                    question=question,
                    result=result,
                    location=location,
                    before_date=before,
                    after_date=after,
                )
            )

            st.session_state.ai_source = (
                "gemini-historical"
            )

            st.session_state.ai_status = (
                None
            )

        except (
            LLMUnavailableError,
            LLMConfigurationError,
        ) as error:

            answer = (
                answer_historical_query(
                    question,
                    result,
                )
            )

            st.session_state.ai_source = (
                "historical-local"
            )

            st.session_state.ai_status = (
                str(error)
            )

        except Exception as error:

            answer = (
                answer_historical_query(
                    question,
                    result,
                )
            )

            st.session_state.ai_source = (
                "historical-local"
            )

            st.session_state.ai_status = (
                f"AI service error: {error}"
            )

    else:

        try:

            answer = (
                ask_gemini(
                    question=question,
                    result=result,
                    location=location,
                    before_date=before,
                    after_date=after,
                )
            )

            st.session_state.ai_source = (
                "gemini"
            )

            st.session_state.ai_status = (
                None
            )

        except (
            LLMUnavailableError,
            LLMConfigurationError,
        ) as error:

            answer = (
                answer_query(
                    question,
                    result,
                )
            )

            st.session_state.ai_source = (
                "fallback"
            )

            st.session_state.ai_status = (
                str(error)
            )

        except Exception as error:

            answer = (
                answer_query(
                    question,
                    result,
                )
            )

            st.session_state.ai_source = (
                "fallback"
            )

            st.session_state.ai_status = (
                f"AI service error: {error}"
            )

    st.session_state.ai_answer = (
        answer
    )


# ==========================================================
# RESPONSE
# ==========================================================

if st.session_state.ai_answer:

    source = (
        st.session_state.ai_source
    )

    if source in (
        "gemini",
        "gemini-historical",
    ):

        st.caption(
            "Generated from the current analysis measurements"
        )

    elif source == "historical-local":

        st.caption(
            "Local response from historical analysis measurements"
        )

    else:

        st.caption(
            "Local response from analysis measurements"
        )

    st.write(
        st.session_state.ai_answer
    )

    if st.session_state.ai_status:

        with st.expander(
            "Service status"
        ):

            st.caption(
                st.session_state.ai_status
            )


# ==========================================================
# METHODOLOGY / METADATA
# ==========================================================

st.divider()

with st.expander(
    "Methodology and metadata"
):

    metadata_left, metadata_right = (
        st.columns(2)
    )

    with metadata_left:

        st.markdown(
            "#### Study"
        )

        st.write(
            f"Mode: `{data['mode_label']}`"
        )

        st.write(
            f"Method: `{data['method']}`"
        )

        st.write(
            "Resolution: "
            f"`~{data['approximate_resolution_m']} m`"
        )

        st.write(
            f"Latitude: `{latitude:.5f}`"
        )

        st.write(
            f"Longitude: `{longitude:.5f}`"
        )

        st.write(
            f"Radius: `{radius} km`"
        )

    with metadata_right:

        st.markdown(
            "#### Time"
        )

        st.write(
            f"Before target: `{before}`"
        )

        st.write(
            f"After target: `{after}`"
        )

        if result.get(
            "date_separation_days"
        ) is not None:

            st.write(
                "Target separation: "
                f"`{result['date_separation_days']} days`"
            )

    if mode == "modern_ml":

        st.markdown(
            "#### Temporal consensus"
        )

        st.write(
            "Per-observation probability: "
            f"`≥ {result.get('confidence_threshold', 0.60) * 100:.0f}%`"
        )

        st.write(
            "Minimum confident observations: "
            f"`{result.get('min_confident_observations', 2)}`"
        )

        st.write(
            "Minimum confidence frequency: "
            f"`≥ {result.get('min_confidence_frequency', 0.50) * 100:.0f}%`"
        )

        st.write(
            "Dominant-class agreement: "
            f"`≥ {result.get('min_temporal_consensus', 0.60) * 100:.0f}%`"
        )

        st.write(
            "Dynamic World observations: "
            f"`{result['before_observations']} / "
            f"{result['after_observations']}`"
        )

        st.write(
            "Sentinel-2 observations: "
            f"`{images['before_sentinel_observations']} / "
            f"{images['after_sentinel_observations']}`"
        )

    else:

        st.markdown(
            "#### Landsat"
        )

        st.write(
            "Before: "
            + sensor_text(
                result[
                    "before_sensors"
                ]
            )
        )

        st.write(
            "After: "
            + sensor_text(
                result[
                    "after_sensors"
                ]
            )
        )

    st.markdown(
        """
#### Limits

Comparable coverage is not classification accuracy.
Target dates are composite centers rather than exact
acquisition dates. Results are satellite-derived
estimates rather than surveyed ground truth.

The application is intended for area-level analysis and
should not be used to claim exact property-level changes
or exact causes of observed differences.
"""
    )


# ==========================================================
# FOOTER
# ==========================================================

st.markdown(
    """
<div class="sq-footer">
    SetQuery · Satellite change analysis
</div>
""",
    unsafe_allow_html=True,
)