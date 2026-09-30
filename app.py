from datetime import date

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
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="SetQuery AI",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================================
# PROFESSIONAL DARK GEOSPATIAL THEME
# ==========================================================

st.markdown(
    """
<style>

:root {
    --bg: #06111a;
    --panel: #0b1b27;

    --border:
        rgba(121, 177, 211, 0.16);

    --cyan: #22c1f6;

    --text: #edf7fd;
    --muted: #8ca7b9;
}


/* =========================================================
   APP
========================================================= */

.stApp {
    background:
        radial-gradient(
            circle at 75% -10%,
            rgba(34, 193, 246, 0.08),
            transparent 34%
        ),
        linear-gradient(
            180deg,
            #07131d,
            #06111a
        );

    color:
        var(--text);
}


.block-container {
    max-width:
        1500px;

    padding-top:
        3.5rem;

    padding-bottom:
        4rem;
}


/* =========================================================
   STREAMLIT CHROME
========================================================= */

#MainMenu,
footer {
    visibility:
        hidden;
}


header[data-testid="stHeader"] {
    background:
        #07131d;

    border-bottom:
        1px solid
        var(--border);
}


/* =========================================================
   SIDEBAR
========================================================= */

section[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            #081722,
            #06121b
        );

    border-right:
        1px solid
        var(--border);
}


/* =========================================================
   BRAND
========================================================= */

.sq-brand {
    display:
        flex;

    align-items:
        center;

    gap:
        12px;

    margin-bottom:
        8px;
}


.sq-brand-icon {
    width:
        42px;

    height:
        42px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    border-radius:
        12px;

    color:
        var(--cyan);

    background:
        rgba(
            34,
            193,
            246,
            0.10
        );

    border:
        1px solid
        rgba(
            34,
            193,
            246,
            0.35
        );
}


.sq-brand-name {
    color:
        white;

    font-weight:
        800;

    letter-spacing:
        0.07em;
}


.sq-brand-sub {
    color:
        #65b6dc;

    font-size:
        11px;

    letter-spacing:
        0.10em;
}


/* =========================================================
   HERO / RESULT
========================================================= */

.sq-hero,
.sq-result {
    padding:
        22px 24px;

    border:
        1px solid
        var(--border);

    border-radius:
        16px;

    background:
        linear-gradient(
            135deg,
            rgba(13, 32, 46, 0.94),
            rgba(9, 25, 36, 0.92)
        );

    margin-bottom:
        20px;
}


.sq-eyebrow {
    color:
        var(--cyan);

    font-size:
        11px;

    font-weight:
        800;

    letter-spacing:
        0.12em;

    text-transform:
        uppercase;
}


.sq-title {
    margin-top:
        6px;

    color:
        #f4faff;

    font-size:
        clamp(
            28px,
            4vw,
            44px
        );

    font-weight:
        760;

    line-height:
        1.1;
}


.sq-location {
    margin-top:
        6px;

    color:
        white;

    font-size:
        25px;

    font-weight:
        720;
}


.sq-meta {
    margin-top:
        8px;

    color:
        var(--muted);

    font-size:
        14px;
}


.sq-mode {
    display:
        inline-flex;

    margin-top:
        12px;

    padding:
        6px 10px;

    border-radius:
        999px;

    border:
        1px solid
        rgba(
            34,
            193,
            246,
            0.32
        );

    background:
        rgba(
            34,
            193,
            246,
            0.08
        );

    color:
        #75d9ff;

    font-size:
        11px;

    font-weight:
        800;

    letter-spacing:
        0.06em;

    text-transform:
        uppercase;
}


/* =========================================================
   SECTION LABEL
========================================================= */

.sq-section {
    color:
        var(--cyan);

    font-size:
        11px;

    font-weight:
        800;

    letter-spacing:
        0.12em;

    text-transform:
        uppercase;

    margin-bottom:
        -7px;
}


/* =========================================================
   METRICS
========================================================= */

div[data-testid="stMetric"] {
    min-height:
        88px;

    padding:
        0.85rem 1rem;

    border:
        1px solid
        var(--border);

    border-radius:
        13px;

    background:
        linear-gradient(
            145deg,
            rgba(14, 34, 49, 0.88),
            rgba(9, 25, 36, 0.88)
        );
}


/* =========================================================
   IMAGES
========================================================= */

div[data-testid="stImage"] img {
    border-radius:
        13px;

    border:
        1px solid
        var(--border);
}


/* =========================================================
   BUTTONS
========================================================= */

div[data-testid="stButton"]
button[kind="primary"],
div[data-testid="stFormSubmitButton"]
button[kind="primary"] {

    width:
        100%;

    min-height:
        46px;

    border:
        0;

    border-radius:
        10px;

    background:
        linear-gradient(
            135deg,
            #087ea9,
            #18a8d6
        );

    color:
        white;

    font-weight:
        750;
}


/* =========================================================
   LEGEND
========================================================= */

.sq-legend {
    display:
        flex;

    flex-wrap:
        wrap;

    gap:
        8px;

    margin-top:
        12px;
}


.sq-legend-item {
    display:
        inline-flex;

    align-items:
        center;

    gap:
        7px;

    padding:
        6px 10px;

    border:
        1px solid
        var(--border);

    border-radius:
        999px;

    color:
        #bcd0dc;

    font-size:
        12px;
}


.sq-dot {
    display:
        inline-block;

    width:
        8px;

    height:
        8px;

    border-radius:
        50%;
}


hr {
    margin:
        2rem 0 !important;

    border-color:
        rgba(
            121,
            177,
            211,
            0.11
        ) !important;
}


/* =========================================================
   RESPONSIVE
========================================================= */

@media (max-width: 900px) {

    .block-container {
        padding-left:
            1rem;

        padding-right:
            1rem;
    }

    .sq-location {
        font-size:
            21px;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ==========================================================
# HELPERS
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
            '<div class="sq-section">'
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

    return ", ".join(
        (
            f"{item['name']} "
            f"({item['observations']} observations)"
        )
        for item in sensor_list
    )


# ==========================================================
# SESSION STATE
# ==========================================================

defaults = {
    "analysis_data":
        None,

    "ai_answer":
        None,

    "ai_source":
        None,

    "ai_status":
        None,
}


for key, value in defaults.items():

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
            '<div class="sq-brand-icon">'
            "◉"
            "</div>"
            "<div>"
            '<div class="sq-brand-name">'
            "SETQUERY AI"
            "</div>"
            '<div class="sq-brand-sub">'
            "GEOSPATIAL INTELLIGENCE"
            "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.caption(
        "Automatic modern / historical "
        "satellite analysis"
    )

    st.divider()

    st.markdown(
        "### New analysis"
    )

    location_name = st.text_input(
        "Location",
        placeholder=(
            "Mumbai, Delhi, London..."
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
            "Mode: Modern ML\n\n"
            "Sentinel-2 + Dynamic World"
        )

    else:

        st.info(
            "Mode: Historical Spectral\n\n"
            "Landsat comparison"
        )

    run_clicked = st.button(
        "RUN SATELLITE ANALYSIS",
        type="primary",
        use_container_width=True,
    )


# ==========================================================
# RUN ANALYSIS
# ==========================================================

if run_clicked:

    # Do not display old results when a new
    # request fails.
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
            "Enter a location."
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
                        "Location not found."
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
                "Unexpected analysis failure."
            )

            with st.expander(
                "Technical details"
            ):

                st.exception(
                    error
                )


# ==========================================================
# LOAD ANALYSIS
# ==========================================================

data = (
    st.session_state.analysis_data
)


# ==========================================================
# EMPTY PAGE
# ==========================================================

if data is None:

    st.markdown(
        (
            '<div class="sq-hero">'
            '<div class="sq-eyebrow">'
            "Satellite Change Intelligence"
            "</div>"
            '<div class="sq-title">'
            "Analyze land change across decades."
            "</div>"
            '<div class="sq-meta">'
            "Modern requests use Sentinel-2 and "
            "Dynamic World ML. Earlier requests use "
            "a common Landsat spectral comparison."
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Modern mode",
        "Sentinel-2 + Dynamic World",
    )

    c2.metric(
        "Historical mode",
        "Landsat Spectral",
    )

    st.info(
        "Enter a study area in the sidebar. "
        "SetQuery AI automatically selects a "
        "compatible analysis methodology."
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
        '<div class="sq-result">'
        '<div class="sq-eyebrow">'
        "ACTIVE ANALYSIS"
        "</div>"
        '<div class="sq-location">'
        f"{location}"
        "</div>"
        '<div class="sq-meta">'
        f"{before} → {after}"
        f" · {radius} km radius"
        "</div>"
        '<div class="sq-mode">'
        f"{data['mode_label']} · "
        f"{data['approximate_resolution_m']} m"
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

    quality = (
        get_coverage_interpretation(
            coverage
        )
    )

    if (
        quality["level"]
        == "VERY LOW"
    ):

        st.error(
            "VERY LOW comparable coverage — "
            f"{quality['description']}"
        )

    elif (
        quality["level"]
        == "LIMITED"
    ):

        st.warning(
            "LIMITED comparable coverage — "
            f"{quality['description']}"
        )

    # ------------------------------------------------------
    # VISUALIZATION
    # ------------------------------------------------------

    section(
        "Visualization",
        "Satellite change viewer",
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

    with before_tab:

        st.image(
            images[
                "before_url"
            ],
            width="stretch",
        )

        st.caption(
            f"Before target: {before} · "
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
            f"After target: {after} · "
            f"{images['after_sentinel_observations']} "
            "Sentinel-2 observations"
        )

    with compare_tab:

        c1, c2 = (
            st.columns(2)
        )

        with c1:

            st.image(
                images[
                    "before_url"
                ],
                caption=(
                    f"Before target · {before}"
                ),
                width="stretch",
            )

        with c2:

            st.image(
                images[
                    "after_url"
                ],
                caption=(
                    f"After target · {after}"
                ),
                width="stretch",
            )

    # ------------------------------------------------------
    # LAND COVER
    # ------------------------------------------------------

    st.divider()

    section(
        "Measurements",
        "Land-cover comparison",
        (
            "Measurements apply only to pixels that passed "
            "the temporal-consensus requirements in both periods."
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

    m1, m2, m3, m4 = (
        st.columns(4)
    )

    m1.metric(
        "Comparable coverage",
        f"{coverage:.1f}%",
    )

    m2.metric(
        "Comparable area",
        (
            f"{result['comparable_area_km2']:.2f} km²"
        ),
    )

    m3.metric(
        "Vegetation net",
        f"{vegetation_change:+.3f} km²",
    )

    m4.metric(
        "Built-up net",
        f"{built_change:+.3f} km²",
    )

    bcol, acol = (
        st.columns(2)
    )

    with bcol:

        st.markdown(
            f"### Before · {before}"
        )

        st.metric(
            "Vegetation",
            (
                f"{result['before_vegetation_km2']:.2f} km²"
            ),
        )

        st.metric(
            "Built-up",
            (
                f"{result['before_built_km2']:.2f} km²"
            ),
        )

        st.metric(
            "Water",
            (
                f"{result['before_water_km2']:.2f} km²"
            ),
        )

        st.metric(
            "Bare ground",
            (
                f"{result['before_bare_km2']:.2f} km²"
            ),
        )

    with acol:

        st.markdown(
            f"### After · {after}"
        )

        st.metric(
            "Vegetation",
            (
                f"{result['after_vegetation_km2']:.2f} km²"
            ),
        )

        st.metric(
            "Built-up",
            (
                f"{result['after_built_km2']:.2f} km²"
            ),
        )

        st.metric(
            "Water",
            (
                f"{result['after_water_km2']:.2f} km²"
            ),
        )

        st.metric(
            "Bare ground",
            (
                f"{result['after_bare_km2']:.2f} km²"
            ),
        )

    st.caption(
        "Coverage is not classification accuracy. "
        "Net differences refer only to the comparable "
        "high-confidence subset."
    )

    # ------------------------------------------------------
    # TRANSITIONS
    # ------------------------------------------------------

    st.divider()

    section(
        "Transitions",
        "High-confidence transitions",
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
            location,
            before,
            after,
            result,
        )
    )


# ==========================================================
# HISTORICAL SPECTRAL MODE
# ==========================================================

else:

    coverage = result[
        "coverage_percent"
    ]

    quality = (
        get_historical_coverage_level(
            coverage
        )
    )

    st.warning(
        "Historical Spectral mode does not use "
        "Dynamic World classification. NDVI, MNDWI "
        "and NDBI are spectral indicators rather than "
        "direct land-cover area measurements."
    )

    if quality == "VERY LOW":

        st.error(
            "Comparable Landsat coverage is very low. "
            "Broad area-level conclusions are not "
            "supported."
        )

    # ------------------------------------------------------
    # HISTORICAL IMAGERY
    # ------------------------------------------------------

    section(
        "Historical imagery",
        "Landsat comparison",
        (
            "Cloud-masked Landsat composites around "
            "the selected target dates."
        ),
    )

    (
        before_tab,
        after_tab,
        compare_tab,
    ) = st.tabs(
        [
            "BEFORE",
            "AFTER",
            "SIDE BY SIDE",
        ]
    )

    with before_tab:

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

    with after_tab:

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

    with compare_tab:

        c1, c2 = (
            st.columns(2)
        )

        with c1:

            st.image(
                images[
                    "before_url"
                ],
                caption=(
                    f"Before · {before}"
                ),
                width="stretch",
            )

        with c2:

            st.image(
                images[
                    "after_url"
                ],
                caption=(
                    f"After · {after}"
                ),
                width="stretch",
            )

    # ------------------------------------------------------
    # SPECTRAL MEASUREMENTS
    # ------------------------------------------------------

    st.divider()

    section(
        "Spectral measurements",
        "Historical comparison",
        (
            "Mean index values are calculated only "
            "where valid Landsat pixels are available "
            "in both periods."
        ),
    )

    h1, h2, h3, h4 = (
        st.columns(4)
    )

    h1.metric(
        "Comparable coverage",
        f"{coverage:.1f}%",
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

    before_indices, after_indices = (
        st.columns(2)
    )

    with before_indices:

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

    with after_indices:

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
        "These are spectral indicators, not direct "
        "categorical area measurements."
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
            location,
            before,
            after,
            result,
        )
    )


# ==========================================================
# SUMMARY
# ==========================================================

st.divider()

section(
    "Grounded interpretation",
    "SetQuery AI analysis",
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
        "Gemini receives only the structured measurements "
        "for the active analysis mode. A deterministic "
        "fallback remains available."
    ),
)


with st.form(
    "question_form",
    clear_on_submit=False,
):

    question = st.text_input(
        "Question",
        placeholder=(
            "What changed in this analysis?"
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
# PROCESS Q&A
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

            answer = ask_gemini(
                question=question,
                result=result,
                location=location,
                before_date=before,
                after_date=after,
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

            answer = answer_query(
                question,
                result,
            )

            st.session_state.ai_source = (
                "fallback"
            )

            st.session_state.ai_status = (
                str(error)
            )

        except Exception as error:

            answer = answer_query(
                question,
                result,
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
# DISPLAY AI RESPONSE
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
            "historical deterministic grounded fallback."
        )

        if st.session_state.ai_status:

            st.caption(
                st.session_state.ai_status
            )

    else:

        st.warning(
            "Gemini unavailable — showing the "
            "local grounded fallback."
        )

        if st.session_state.ai_status:

            st.caption(
                st.session_state.ai_status
            )

    st.write(
        st.session_state.ai_answer
    )


# ==========================================================
# METADATA
# ==========================================================

st.divider()

with st.expander(
    "Analysis metadata & limitations"
):

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
        f"Latitude: `{data['latitude']:.5f}`"
    )

    st.write(
        f"Longitude: `{data['longitude']:.5f}`"
    )

    st.write(
        f"Requested radius: `{radius} km`"
    )

    st.write(
        f"Before target date: `{before}`"
    )

    st.write(
        f"After target date: `{after}`"
    )

    if mode == "historical_spectral":

        st.markdown(
            "#### Landsat sensors"
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
            "#### Historical-mode limitations"
        )

        st.write(
            "Historical mode compares spectral indices "
            "rather than Dynamic World land-cover classes."
        )

        st.write(
            "Different Landsat generations can have "
            "spectral bandpass differences that influence "
            "absolute index values."
        )

        st.write(
            "NDBI responds to built and bare surfaces and "
            "must not be interpreted as exact built-up area."
        )

    else:

        st.markdown(
            "#### Modern-mode observations"
        )

        st.write(
            "Dynamic World before: "
            f"`{result['before_observations']}`"
        )

        st.write(
            "Dynamic World after: "
            f"`{result['after_observations']}`"
        )

        st.write(
            "Sentinel-2 before: "
            f"`{images['before_sentinel_observations']}`"
        )

        st.write(
            "Sentinel-2 after: "
            f"`{images['after_sentinel_observations']}`"
        )

    st.markdown(
        """
#### General interpretation boundaries

- Results are satellite-derived estimates rather than surveyed ground truth.
- Target dates represent composite centers rather than exact acquisition dates.
- Comparable coverage is not classification accuracy.
- The system is intended for area-level analysis.
- It should not claim exact property-level changes or exact causes.
"""
    )