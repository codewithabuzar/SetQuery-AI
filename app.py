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

APP_NAME = "SETQUERY AI"

CONFIDENCE_THRESHOLD = 0.60

RADIUS_MIN_KM = 1
RADIUS_MAX_KM = 20
RADIUS_DEFAULT_KM = 10


# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="SetQuery AI",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================================
# EXTERNAL STYLESHEET
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
    """
    Render a consistent section heading.
    """

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
    """
    Format Landsat sensor metadata.
    """

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
    """
    Return UI status class for a coverage category.
    """

    if level == "GOOD":
        return "sq-status-good"

    if level in (
        "MODERATE",
        "LIMITED",
    ):
        return "sq-status-warning"

    return "sq-status-danger"


def render_status_strip(
    text,
    level,
):
    """
    Render a styled quality/status strip.
    """

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


# ==========================================================
# CHART HELPERS
# ==========================================================

def modern_land_cover_chart(
    result,
):
    """
    Build grouped Before/After Modern ML land-cover chart.
    """

    values = [
        {
            "Class":
                "Vegetation",

            "Period":
                "Before",

            "Area":
                result[
                    "before_vegetation_km2"
                ],
        },

        {
            "Class":
                "Vegetation",

            "Period":
                "After",

            "Area":
                result[
                    "after_vegetation_km2"
                ],
        },

        {
            "Class":
                "Built-up",

            "Period":
                "Before",

            "Area":
                result[
                    "before_built_km2"
                ],
        },

        {
            "Class":
                "Built-up",

            "Period":
                "After",

            "Area":
                result[
                    "after_built_km2"
                ],
        },

        {
            "Class":
                "Water",

            "Period":
                "Before",

            "Area":
                result[
                    "before_water_km2"
                ],
        },

        {
            "Class":
                "Water",

            "Period":
                "After",

            "Area":
                result[
                    "after_water_km2"
                ],
        },

        {
            "Class":
                "Bare",

            "Period":
                "Before",

            "Area":
                result[
                    "before_bare_km2"
                ],
        },

        {
            "Class":
                "Bare",

            "Period":
                "After",

            "Area":
                result[
                    "after_bare_km2"
                ],
        },
    ]

    chart = (
        alt.Chart(
            alt.Data(
                values=values
            )
        )
        .mark_bar(
            cornerRadiusTopLeft=3,
            cornerRadiusTopRight=3,
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
                        "#64748b",
                        "#22c1f6",
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
                    title="Class",
                ),

                alt.Tooltip(
                    "Period:N",
                    title="Period",
                ),

                alt.Tooltip(
                    "Area:Q",
                    title="Area (km²)",
                    format=".3f",
                ),
            ],
        )
        .properties(
            height=280
        )
        .configure_view(
            strokeOpacity=0
        )
        .configure_axis(
            labelColor="#9fb6c5",
            titleColor="#9fb6c5",
            gridColor="#173244",
            domainColor="#294657",
            tickColor="#294657",
        )
        .configure_legend(
            labelColor="#b7cbd7"
        )
    )

    return chart


def historical_index_chart(
    result,
):
    """
    Build grouped Before/After historical index chart.
    """

    values = [
        {
            "Index":
                "NDVI",

            "Period":
                "Before",

            "Value":
                result[
                    "before_mean_ndvi"
                ],
        },

        {
            "Index":
                "NDVI",

            "Period":
                "After",

            "Value":
                result[
                    "after_mean_ndvi"
                ],
        },

        {
            "Index":
                "MNDWI",

            "Period":
                "Before",

            "Value":
                result[
                    "before_mean_mndwi"
                ],
        },

        {
            "Index":
                "MNDWI",

            "Period":
                "After",

            "Value":
                result[
                    "after_mean_mndwi"
                ],
        },

        {
            "Index":
                "NDBI",

            "Period":
                "Before",

            "Value":
                result[
                    "before_mean_ndbi"
                ],
        },

        {
            "Index":
                "NDBI",

            "Period":
                "After",

            "Value":
                result[
                    "after_mean_ndbi"
                ],
        },
    ]

    chart = (
        alt.Chart(
            alt.Data(
                values=values
            )
        )
        .mark_bar(
            cornerRadiusTopLeft=3,
            cornerRadiusTopRight=3,
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
                        "#64748b",
                        "#22c1f6",
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
                    title="Index",
                ),

                alt.Tooltip(
                    "Period:N",
                    title="Period",
                ),

                alt.Tooltip(
                    "Value:Q",
                    title="Value",
                    format=".3f",
                ),
            ],
        )
        .properties(
            height=280
        )
        .configure_view(
            strokeOpacity=0
        )
        .configure_axis(
            labelColor="#9fb6c5",
            titleColor="#9fb6c5",
            gridColor="#173244",
            domainColor="#294657",
            tickColor="#294657",
        )
        .configure_legend(
            labelColor="#b7cbd7"
        )
    )

    return chart


# ==========================================================
# SESSION STATE
# ==========================================================

SESSION_DEFAULTS = {
    "analysis_data":
        None,

    "ai_answer":
        None,

    "ai_source":
        None,

    "ai_status":
        None,
}


for key, value in (
    SESSION_DEFAULTS.items()
):

    if key not in st.session_state:

        st.session_state[
            key
        ] = value


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:

    st.markdown(
        (
            '<div class="sq-brand">'
            '<div class="sq-brand-icon">◉</div>'
            "<div>"
            '<div class="sq-brand-name">'
            "SETQUERY AI"
            "</div>"
            '<div class="sq-brand-sub">'
            "Geospatial Intelligence"
            "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.caption(
        "Satellite change analysis across "
        "modern and historical periods."
    )

    st.divider()

    st.markdown(
        "### New analysis"
    )

    location_name = st.text_input(
        "Location",
        placeholder=(
            "e.g. Mumbai, Maharashtra, India"
        ),
    )

    before_date = st.date_input(
        "Before target date",
        value=date(
            2022,
            9,
            15,
        ),
    )

    after_date = st.date_input(
        "After target date",
        value=date(
            2025,
            9,
            15,
        ),
    )

    radius_km = st.slider(
        "Analysis radius",
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

        st.info(
            "MODERN ML\n\n"
            "Sentinel-2 + Dynamic World "
            "Temporal Consensus"
        )

    else:

        st.info(
            "HISTORICAL SPECTRAL\n\n"
            "Landsat · NDVI · MNDWI · NDBI"
        )

    st.caption(
        "Selected dates are composite target dates, "
        "not exact satellite acquisition dates."
    )

    run_clicked = st.button(
        "RUN SATELLITE ANALYSIS",
        type="primary",
        use_container_width=True,
    )

    st.divider()

    st.caption(
        "Area-level satellite estimates · "
        "Not surveyed ground truth"
    )


# ==========================================================
# RUN ANALYSIS
# ==========================================================

if run_clicked:

    # Clear old results before a new request.
    # A failed request must never display stale results.
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

    if not location_name.strip():

        st.error(
            "Enter a location before running analysis."
        )

    else:

        try:

            with st.spinner(
                "Running satellite analysis..."
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

            st.success(
                "Analysis completed."
            )

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
                "The analysis could not be completed "
                "because of an unexpected service or "
                "network error."
            )

            with st.expander(
                "Technical details"
            ):

                st.exception(
                    error
                )


# ==========================================================
# LOAD ACTIVE ANALYSIS
# ==========================================================

data = (
    st.session_state.analysis_data
)


# ==========================================================
# LANDING STATE
# ==========================================================

if data is None:

    st.markdown(
        (
            '<div class="sq-hero">'
            '<div class="sq-eyebrow">'
            "Satellite Change Intelligence"
            "</div>"
            '<div class="sq-title">'
            "Understand land change across decades."
            "</div>"
            '<div class="sq-copy">'
            "SetQuery AI automatically selects a "
            "satellite-analysis methodology based on "
            "the requested time period. Modern analysis "
            "uses Sentinel-2 and Dynamic World ML; "
            "historical analysis uses Landsat spectral "
            "comparison."
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    e1, e2, e3 = (
        st.columns(3)
    )

    e1.metric(
        "Modern analysis",
        "~10 m",
        "Sentinel-2 + DW",
    )

    e2.metric(
        "Historical analysis",
        "~30 m",
        "Landsat",
    )

    e3.metric(
        "AI explanation",
        "Grounded",
        "Gemini + fallback",
    )

    st.info(
        "SetQuery AI is intended for area-level "
        "satellite analysis. It should not be used "
        "for exact property-level or surveyed-ground-"
        "truth claims."
    )

    st.stop()


# ==========================================================
# COMMON RESULT VARIABLES
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
# ACTIVE ANALYSIS HEADER
# ==========================================================

st.markdown(
    (
        '<div class="sq-result-header">'
        '<div class="sq-eyebrow">'
        "Active satellite analysis"
        "</div>"
        '<div class="sq-location">'
        f"{location}"
        "</div>"
        '<div class="sq-meta">'
        f"{before} → {after}"
        " &nbsp;·&nbsp; "
        f"{radius} km radius"
        "</div>"
        '<div class="sq-badge-row">'
        '<span class="sq-badge">'
        f"{data['mode_label']}"
        "</span>"
        '<span class="sq-badge">'
        f"~{data['approximate_resolution_m']} m"
        "</span>"
        "</div>"
        "</div>"
    ),
    unsafe_allow_html=True,
)


# ==========================================================
# MODERN ML MODE
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

    render_status_strip(
        (
            f"{coverage_level} temporal-consensus "
            f"coverage · {coverage:.1f}% · "
            f"{coverage_info['description']}"
        ),
        coverage_level,
    )

    # ------------------------------------------------------
    # VISUALIZATION WORKSPACE
    # ------------------------------------------------------

    section(
        "Visualization workspace",
        "Satellite change viewer",
        (
            "Compare the temporal-consensus change map "
            "with cloud-masked Sentinel-2 composites."
        ),
    )

    (
        change_tab,
        before_tab,
        after_tab,
        compare_tab,
    ) = st.tabs(
        [
            "CHANGE MAP",
            "BEFORE",
            "AFTER",
            "SIDE BY SIDE",
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

        legend_html = (
            '<div class="sq-legend">'

            '<span class="sq-legend-item">'
            '<span class="sq-dot" '
            'style="background:#ff0000"></span>'
            "Vegetation → Built-up"
            "</span>"

            '<span class="sq-legend-item">'
            '<span class="sq-dot" '
            'style="background:#00ff00"></span>'
            "Built-up → Vegetation"
            "</span>"

            '<span class="sq-legend-item">'
            '<span class="sq-dot" '
            'style="background:#ffff00"></span>'
            "Bare → Built-up"
            "</span>"

            '<span class="sq-legend-item">'
            '<span class="sq-dot" '
            'style="background:#0066ff"></span>'
            "Non-water → Water"
            "</span>"

            '<span class="sq-legend-item">'
            '<span class="sq-dot" '
            'style="background:#ff8800"></span>'
            "Water → Non-water"
            "</span>"

            "</div>"
        )

        st.markdown(
            legend_html,
            unsafe_allow_html=True,
        )

        st.caption(
            "Colored transition pixels may be enlarged "
            "for visual clarity. Numerical statistics "
            "use the original classification pixels."
        )

    with before_tab:

        st.image(
            images[
                "before_url"
            ],
            width="stretch",
        )

        st.caption(
            f"Target: {before} · "
            f"{images['before_sentinel_observations']} "
            "Sentinel-2 observations"
        )

    with after_tab:

        st.image(
            images[
                "after_url"
            ],
            width="stretch",
        )

        st.caption(
            f"Target: {after} · "
            f"{images['after_sentinel_observations']} "
            "Sentinel-2 observations"
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
    # MODERN SNAPSHOT
    # ------------------------------------------------------

    st.divider()

    section(
        "Confidence-aware measurements",
        "Comparison snapshot",
        (
            "Measurements apply only to pixels that "
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

    water_change = (
        result[
            "after_water_km2"
        ]
        -
        result[
            "before_water_km2"
        ]
    )

    snapshot1, snapshot2, snapshot3, snapshot4 = (
        st.columns(4)
    )

    snapshot1.metric(
        "Comparable coverage",
        f"{coverage:.1f}%",
    )

    snapshot2.metric(
        "Comparable area",
        (
            f"{result['comparable_area_km2']:.2f} km²"
        ),
    )

    snapshot3.metric(
        "Vegetation net",
        f"{vegetation_change:+.3f} km²",
    )

    snapshot4.metric(
        "Built-up net",
        f"{built_change:+.3f} km²",
    )

    # ------------------------------------------------------
    # MODERN CHART
    # ------------------------------------------------------

    st.markdown(
        (
            '<div class="sq-chart-title">'
            "LAND-COVER PROFILE"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.altair_chart(
        modern_land_cover_chart(
            result
        ),
        width="stretch",
    )

    # ------------------------------------------------------
    # BEFORE / AFTER VALUES
    # ------------------------------------------------------

    before_stats, after_stats = (
        st.columns(2)
    )

    with before_stats:

        st.markdown(
            f"### Before · {before}"
        )

        bc1, bc2 = (
            st.columns(2)
        )

        bc1.metric(
            "Vegetation",
            (
                f"{result['before_vegetation_km2']:.2f} km²"
            ),
        )

        bc2.metric(
            "Built-up",
            (
                f"{result['before_built_km2']:.2f} km²"
            ),
        )

        bc3, bc4 = (
            st.columns(2)
        )

        bc3.metric(
            "Water",
            (
                f"{result['before_water_km2']:.2f} km²"
            ),
        )

        bc4.metric(
            "Bare ground",
            (
                f"{result['before_bare_km2']:.2f} km²"
            ),
        )

    with after_stats:

        st.markdown(
            f"### After · {after}"
        )

        ac1, ac2 = (
            st.columns(2)
        )

        ac1.metric(
            "Vegetation",
            (
                f"{result['after_vegetation_km2']:.2f} km²"
            ),
        )

        ac2.metric(
            "Built-up",
            (
                f"{result['after_built_km2']:.2f} km²"
            ),
        )

        ac3, ac4 = (
            st.columns(2)
        )

        ac3.metric(
            "Water",
            (
                f"{result['after_water_km2']:.2f} km²"
            ),
        )

        ac4.metric(
            "Bare ground",
            (
                f"{result['after_bare_km2']:.2f} km²"
            ),
        )

    st.caption(
        "Coverage is not classification accuracy. "
        "Net differences and explicit transitions are "
        "different measurements."
    )

    # ------------------------------------------------------
    # TRANSITIONS
    # ------------------------------------------------------

    st.divider()

    section(
        "Change matrix",
        "Detected transitions",
        (
            "Selected explicit before-to-after "
            "land-cover transitions."
        ),
    )

    t1, t2, t3 = (
        st.columns(3)
    )

    t1.metric(
        "Vegetation → Built",
        (
            f"{result['vegetation_to_built_km2']:.4f} km²"
        ),
    )

    t2.metric(
        "Built → Vegetation",
        (
            f"{result['built_to_vegetation_km2']:.4f} km²"
        ),
    )

    t3.metric(
        "Bare → Built",
        (
            f"{result['bare_to_built_km2']:.4f} km²"
        ),
    )

    t4, t5 = (
        st.columns(2)
    )

    t4.metric(
        "Water → Non-water",
        (
            f"{result['water_to_nonwater_km2']:.4f} km²"
        ),
    )

    t5.metric(
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
# HISTORICAL SPECTRAL MODE
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

    render_status_strip(
        (
            f"{coverage_level} comparable spatial "
            f"coverage · {coverage:.1f}%. "
            "Historical mode measures spectral indices "
            "rather than Dynamic World land-cover classes."
        ),
        coverage_level,
    )

    # ------------------------------------------------------
    # HISTORICAL SOURCE SUPPORT
    # ------------------------------------------------------

    section(
        "Data support",
        "Landsat source observations",
        (
            "Spatial coverage and temporal source support "
            "are different concepts. Neither is accuracy."
        ),
    )

    support1, support2, support3 = (
        st.columns(3)
    )

    support1.metric(
        "Spatial coverage",
        f"{coverage:.1f}%",
        coverage_level,
    )

    support2.metric(
        "BEFORE source support",
        source_support[
            "before_level"
        ],
        (
            f"{source_support['before_count']} "
            "observation(s)"
        ),
    )

    support3.metric(
        "AFTER source support",
        source_support[
            "after_level"
        ],
        (
            f"{source_support['after_count']} "
            "observation(s)"
        ),
    )

    support_warnings = (
        get_historical_support_warnings(
            result
        )
    )

    for warning in (
        support_warnings
    ):

        st.warning(
            warning
        )

    # ------------------------------------------------------
    # HISTORICAL IMAGERY
    # ------------------------------------------------------

    st.divider()

    section(
        "Historical imagery",
        "Landsat comparison",
        (
            "Cloud-masked Landsat composites around "
            "the selected target dates."
        ),
    )

    (
        historical_before_tab,
        historical_after_tab,
        historical_compare_tab,
    ) = st.tabs(
        [
            "BEFORE",
            "AFTER",
            "SIDE BY SIDE",
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
            "Sensors: "
            + sensor_text(
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
            "Sensors: "
            + sensor_text(
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
    # HISTORICAL SPECTRAL ANALYSIS
    # ------------------------------------------------------

    st.divider()

    section(
        "Spectral measurements",
        "Historical comparison",
        (
            "Mean index values are calculated only where "
            "valid Landsat pixels are available in both "
            "periods."
        ),
    )

    h1, h2, h3, h4 = (
        st.columns(4)
    )

    h1.metric(
        "Comparable area",
        (
            f"{result['comparable_area_km2']:.2f} km²"
        ),
    )

    h2.metric(
        "NDVI Δ",
        (
            f"{result['ndvi_change']:+.3f}"
        ),
    )

    h3.metric(
        "MNDWI Δ",
        (
            f"{result['mndwi_change']:+.3f}"
        ),
    )

    h4.metric(
        "NDBI Δ",
        (
            f"{result['ndbi_change']:+.3f}"
        ),
    )

    st.markdown(
        (
            '<div class="sq-chart-title">'
            "SPECTRAL INDEX PROFILE"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.altair_chart(
        historical_index_chart(
            result
        ),
        width="stretch",
    )

    historical_values_before, historical_values_after = (
        st.columns(2)
    )

    with historical_values_before:

        st.markdown(
            f"### Before · {before}"
        )

        st.metric(
            "Mean NDVI",
            (
                f"{result['before_mean_ndvi']:.3f}"
            ),
        )

        st.metric(
            "Mean MNDWI",
            (
                f"{result['before_mean_mndwi']:.3f}"
            ),
        )

        st.metric(
            "Mean NDBI",
            (
                f"{result['before_mean_ndbi']:.3f}"
            ),
        )

    with historical_values_after:

        st.markdown(
            f"### After · {after}"
        )

        st.metric(
            "Mean NDVI",
            (
                f"{result['after_mean_ndvi']:.3f}"
            ),
        )

        st.metric(
            "Mean MNDWI",
            (
                f"{result['after_mean_mndwi']:.3f}"
            ),
        )

        st.metric(
            "Mean NDBI",
            (
                f"{result['after_mean_ndbi']:.3f}"
            ),
        )

    st.caption(
        "NDVI is vegetation-related, MNDWI is "
        "water-related, and NDBI is built/bare-related. "
        "These indices are not direct categorical "
        "land-cover area measurements."
    )

    # Existing engine warnings:
    # Landsat 7, cross-sensor effects, NDBI limitation, etc.
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
# DETERMINISTIC ANALYSIS SUMMARY
# ==========================================================

st.divider()

section(
    "Grounded interpretation",
    "SetQuery AI analysis",
    (
        "Generated deterministically from the measured "
        "analysis results."
    ),
)

st.info(
    summary
)


# ==========================================================
# GROUNDED Q&A
# ==========================================================

st.divider()

section(
    "Grounded Q&A",
    "Ask SetQuery AI",
    (
        "Gemini receives only structured measurements "
        "from the active analysis. A deterministic local "
        "fallback remains available."
    ),
)


with st.form(
    "question_form",
    clear_on_submit=False,
):

    question = st.text_input(
        "Question about this analysis",
        placeholder=(
            "e.g. What are the most important changes?"
        ),
    )

    ask_clicked = (
        st.form_submit_button(
            "ASK SETQUERY AI",
            type="primary",
            use_container_width=True,
        )
    )


# ==========================================================
# PROCESS AI QUESTION
# ==========================================================

if (
    ask_clicked
    and question.strip()
):

    # ------------------------------------------------------
    # HISTORICAL GEMINI
    # ------------------------------------------------------

    if mode == "historical_spectral":

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
                f"Unexpected AI error: {error}"
            )

    # ------------------------------------------------------
    # MODERN GEMINI
    # ------------------------------------------------------

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
                f"Unexpected AI error: {error}"
            )

    st.session_state.ai_answer = (
        answer
    )


# ==========================================================
# AI RESPONSE
# ==========================================================

if st.session_state.ai_answer:

    source = (
        st.session_state.ai_source
    )

    if source == "gemini":

        st.success(
            "Gemini grounded response · Modern ML"
        )

    elif (
        source
        == "gemini-historical"
    ):

        st.success(
            "Gemini grounded response · "
            "Historical Spectral"
        )

    elif (
        source
        == "historical-local"
    ):

        st.warning(
            "Gemini unavailable — showing the "
            "historical deterministic fallback."
        )

        if st.session_state.ai_status:

            st.caption(
                st.session_state.ai_status
            )

    else:

        st.warning(
            "Gemini unavailable — showing the "
            "local deterministic fallback."
        )

        if st.session_state.ai_status:

            st.caption(
                st.session_state.ai_status
            )

    st.write(
        st.session_state.ai_answer
    )


# ==========================================================
# TECHNICAL METADATA
# ==========================================================

st.divider()

with st.expander(
    "Analysis metadata & methodology"
):

    metadata_left, metadata_right = (
        st.columns(2)
    )

    with metadata_left:

        st.markdown(
            "#### Request"
        )

        st.write(
            f"Mode: `{data['mode_label']}`"
        )

        st.write(
            f"Method: `{data['method']}`"
        )

        st.write(
            "Approximate spatial resolution: "
            f"`{data['approximate_resolution_m']} m`"
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
            "#### Timing"
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
                "Target-date separation: "
                f"`{result['date_separation_days']} days`"
            )


    if mode == "modern_ml":

        st.markdown(
            "#### Dynamic World temporal consensus"
        )

        st.write(
            "Per-observation probability threshold: "
            f"`{result.get('confidence_threshold', 0.60) * 100:.0f}%`"
        )

        st.write(
            "Minimum confident observations: "
            f"`{result.get('min_confident_observations', 2)}`"
        )

        st.write(
            "Minimum confidence frequency: "
            f"`{result.get('min_confidence_frequency', 0.50) * 100:.0f}%`"
        )

        st.write(
            "Minimum dominant-class agreement: "
            f"`{result.get('min_temporal_consensus', 0.60) * 100:.0f}%`"
        )

        st.write(
            "Dynamic World observations before: "
            f"`{result['before_observations']}`"
        )

        st.write(
            "Dynamic World observations after: "
            f"`{result['after_observations']}`"
        )

        st.write(
            "Sentinel-2 observations before: "
            f"`{images['before_sentinel_observations']}`"
        )

        st.write(
            "Sentinel-2 observations after: "
            f"`{images['after_sentinel_observations']}`"
        )

    else:

        st.markdown(
            "#### Landsat source metadata"
        )

        st.write(
            "Before sensors: "
            + sensor_text(
                result[
                    "before_sensors"
                ]
            )
        )

        st.write(
            "After sensors: "
            + sensor_text(
                result[
                    "after_sensors"
                ]
            )
        )

        st.write(
            "BEFORE source support: "
            f"`{source_support['before_level']}`"
        )

        st.write(
            "AFTER source support: "
            f"`{source_support['after_level']}`"
        )


    st.markdown(
        """
#### Interpretation boundaries

- Comparable coverage is not classification accuracy.
- Target dates are composite centers, not necessarily exact acquisition dates.
- Results are satellite-derived estimates rather than surveyed ground truth.
- Modern transition-map enlargement is visualization-only; numerical statistics use original pixels.
- Historical NDVI, MNDWI and NDBI are spectral indicators rather than direct categorical area measurements.
- The application is intended for area-level analysis rather than exact property-level change detection.
"""
    )


# ==========================================================
# FOOTER
# ==========================================================

st.markdown(
    (
        '<div class="sq-footer">'
        "SETQUERY AI · Sentinel-2 · Dynamic World · "
        "Landsat · Grounded AI Analysis"
        "</div>"
    ),
    unsafe_allow_html=True,
)