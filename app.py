from datetime import date

import streamlit as st
from geopy.geocoders import Nominatim

from analysis import (
    analyze_area,
    get_satellite_images,
    get_change_map,
    AnalysisValidationError,
    AnalysisDataError,
)
from report import (
    generate_analysis_summary,
    get_coverage_interpretation,
)
from query import answer_query
from llm import (
    ask_gemini,
    LLMUnavailableError,
    LLMConfigurationError,
)


# ==========================================================
# APP CONFIGURATION
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
# PROFESSIONAL GEOSPATIAL THEME
# ==========================================================

st.markdown(
    """
<style>

:root {
    --sq-bg: #071019;
    --sq-bg-2: #0a1520;

    --sq-panel: rgba(13, 27, 40, 0.90);
    --sq-panel-2: rgba(16, 34, 49, 0.78);

    --sq-border: rgba(123, 174, 209, 0.16);
    --sq-border-strong: rgba(56, 189, 248, 0.35);

    --sq-text: #eaf4fb;
    --sq-muted: #8faabd;

    --sq-accent: #27c2ff;
    --sq-accent-2: #5b8cff;

    --sq-green: #3ddc97;
    --sq-yellow: #facc15;
    --sq-orange: #fb923c;
    --sq-red: #fb5d68;

    --sq-radius: 16px;
}


/* ---------------------------------------------------------
   APPLICATION FOUNDATION
--------------------------------------------------------- */

html,
body,
[class*="css"] {
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}


.stApp {
    background:
        radial-gradient(
            circle at 80% 0%,
            rgba(39, 194, 255, 0.08),
            transparent 30%
        ),
        radial-gradient(
            circle at 10% 20%,
            rgba(91, 140, 255, 0.06),
            transparent 25%
        ),
        linear-gradient(
            180deg,
            #071019 0%,
            #08121b 50%,
            #061019 100%
        );

    color: var(--sq-text);
}


.block-container {
    max-width: 1500px;

    padding-top: 1.5rem;
    padding-bottom: 4rem;
}


/* ---------------------------------------------------------
   STREAMLIT CHROME
--------------------------------------------------------- */

#MainMenu {
    visibility: hidden;
}


footer {
    visibility: hidden;
}


header[data-testid="stHeader"] {
    background:
        rgba(7, 16, 25, 0.72);

    backdrop-filter:
        blur(10px);
}


/* ---------------------------------------------------------
   SIDEBAR
--------------------------------------------------------- */

section[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            rgba(9, 21, 32, 0.98),
            rgba(6, 15, 23, 0.98)
        );

    border-right:
        1px solid var(--sq-border);
}


section[data-testid="stSidebar"] > div {
    padding-top: 1rem;
}


/* ---------------------------------------------------------
   INPUTS
--------------------------------------------------------- */

div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] {
    background:
        rgba(8, 20, 30, 0.90) !important;

    border-color:
        var(--sq-border) !important;
}


div[data-baseweb="input"]:focus-within > div {
    border-color:
        var(--sq-accent) !important;
}


div[data-testid="stDateInput"] input,
div[data-testid="stTextInput"] input {
    color:
        var(--sq-text) !important;
}


/* ---------------------------------------------------------
   BUTTONS
--------------------------------------------------------- */

div[data-testid="stButton"]
button[kind="primary"],
div[data-testid="stFormSubmitButton"]
button[kind="primary"] {

    width: 100%;
    min-height: 3rem;

    border:
        1px solid rgba(
            39,
            194,
            255,
            0.45
        );

    border-radius: 10px;

    background:
        linear-gradient(
            135deg,
            #087aa8,
            #159fcf
        );

    color: white;

    font-weight: 700;
    letter-spacing: 0.025em;

    box-shadow:
        0 8px 24px
        rgba(0, 153, 204, 0.16);

    transition:
        transform 0.15s ease,
        border-color 0.15s ease,
        box-shadow 0.15s ease;
}


div[data-testid="stButton"]
button[kind="primary"]:hover,
div[data-testid="stFormSubmitButton"]
button[kind="primary"]:hover {

    transform:
        translateY(-1px);

    border-color:
        var(--sq-accent);

    box-shadow:
        0 10px 30px
        rgba(0, 174, 232, 0.24);
}


/* ---------------------------------------------------------
   METRIC CARDS
--------------------------------------------------------- */

div[data-testid="stMetric"] {
    min-height: 110px;

    padding:
        1rem 1.1rem;

    border:
        1px solid var(--sq-border);

    border-radius:
        14px;

    background:
        linear-gradient(
            145deg,
            rgba(17, 35, 50, 0.86),
            rgba(9, 23, 34, 0.86)
        );

    box-shadow:
        0 10px 30px
        rgba(0, 0, 0, 0.10);
}


div[data-testid="stMetricLabel"] {
    color: var(--sq-muted);
}


div[data-testid="stMetricValue"] {
    color: var(--sq-text);
}


/* ---------------------------------------------------------
   IMAGERY
--------------------------------------------------------- */

div[data-testid="stImage"] img {
    border-radius:
        14px;

    border:
        1px solid
        rgba(104, 159, 195, 0.18);

    box-shadow:
        0 14px 35px
        rgba(0, 0, 0, 0.18);
}


/* ---------------------------------------------------------
   DIVIDERS
--------------------------------------------------------- */

hr {
    margin-top:
        2rem !important;

    margin-bottom:
        2rem !important;

    border-color:
        rgba(
            118,
            164,
            194,
            0.12
        ) !important;
}


/* ---------------------------------------------------------
   TYPOGRAPHY
--------------------------------------------------------- */

h1,
h2,
h3 {
    letter-spacing:
        -0.025em;
}


h2 {
    color:
        #e6f5ff !important;
}


p {
    line-height:
        1.65;
}


/* ---------------------------------------------------------
   BRAND
--------------------------------------------------------- */

.sq-brand {
    display: flex;

    align-items:
        center;

    gap:
        0.8rem;

    margin-bottom:
        1rem;
}


.sq-brand-mark {
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

    background:
        linear-gradient(
            145deg,
            rgba(39, 194, 255, 0.20),
            rgba(91, 140, 255, 0.12)
        );

    border:
        1px solid
        rgba(39, 194, 255, 0.30);

    font-size:
        1.25rem;
}


.sq-brand-title {
    font-size:
        1.15rem;

    font-weight:
        800;

    letter-spacing:
        0.06em;
}


.sq-brand-subtitle {
    color:
        var(--sq-muted);

    font-size:
        0.73rem;

    letter-spacing:
        0.08em;

    text-transform:
        uppercase;
}


/* ---------------------------------------------------------
   HERO
--------------------------------------------------------- */

.sq-hero {
    padding:
        1.4rem
        1.5rem;

    margin-bottom:
        1.2rem;

    border:
        1px solid var(--sq-border);

    border-radius:
        18px;

    background:
        linear-gradient(
            135deg,
            rgba(18, 39, 56, 0.75),
            rgba(9, 25, 37, 0.72)
        );

    box-shadow:
        0 18px 45px
        rgba(0, 0, 0, 0.13);
}


.sq-eyebrow {
    color:
        var(--sq-accent);

    font-size:
        0.72rem;

    font-weight:
        750;

    letter-spacing:
        0.12em;

    text-transform:
        uppercase;

    margin-bottom:
        0.55rem;
}


.sq-hero-title {
    margin:
        0;

    color:
        #f2f9ff;

    font-size:
        clamp(
            1.8rem,
            3vw,
            2.8rem
        );

    line-height:
        1.05;

    font-weight:
        760;
}


.sq-hero-copy {
    max-width:
        850px;

    margin-top:
        0.8rem;

    margin-bottom:
        0;

    color:
        var(--sq-muted);

    font-size:
        0.98rem;
}


/* ---------------------------------------------------------
   SECTION HEADERS
--------------------------------------------------------- */

.sq-section-kicker {
    color:
        var(--sq-accent);

    font-size:
        0.72rem;

    font-weight:
        750;

    letter-spacing:
        0.11em;

    text-transform:
        uppercase;

    margin-bottom:
        -0.5rem;
}


/* ---------------------------------------------------------
   LOCATION
--------------------------------------------------------- */

.sq-location-card {
    padding:
        1rem 1.1rem;

    border:
        1px solid var(--sq-border);

    border-radius:
        14px;

    background:
        rgba(
            12,
            28,
            41,
            0.72
        );

    color:
        var(--sq-text);

    margin-bottom:
        1rem;
}


.sq-location-card strong {
    display:
        block;

    margin-bottom:
        0.3rem;

    color:
        var(--sq-accent);

    font-size:
        0.75rem;

    text-transform:
        uppercase;

    letter-spacing:
        0.08em;
}


/* ---------------------------------------------------------
   TAGS
--------------------------------------------------------- */

.sq-tag-row {
    display:
        flex;

    flex-wrap:
        wrap;

    gap:
        0.5rem;

    margin-top:
        0.75rem;
}


.sq-tag {
    display:
        inline-flex;

    align-items:
        center;

    min-height:
        30px;

    padding:
        0.35rem
        0.7rem;

    border-radius:
        999px;

    border:
        1px solid var(--sq-border);

    background:
        rgba(
            8,
            23,
            34,
            0.75
        );

    color:
        #bcd1df;

    font-size:
        0.77rem;
}


/* ---------------------------------------------------------
   CHANGE LEGEND
--------------------------------------------------------- */

.sq-legend {
    display:
        flex;

    flex-wrap:
        wrap;

    gap:
        0.6rem;

    margin:
        0.85rem
        0
        0.7rem;
}


.sq-legend-item {
    display:
        inline-flex;

    align-items:
        center;

    gap:
        0.45rem;

    padding:
        0.38rem
        0.65rem;

    border:
        1px solid var(--sq-border);

    border-radius:
        999px;

    color:
        #c7d9e5;

    background:
        rgba(
            8,
            21,
            31,
            0.72
        );

    font-size:
        0.76rem;
}


.sq-dot {
    width:
        8px;

    height:
        8px;

    display:
        inline-block;

    flex:
        0 0 8px;

    border-radius:
        50%;
}


/* ---------------------------------------------------------
   INFORMATION CONTEXT
--------------------------------------------------------- */

.sq-context {
    padding:
        0.9rem
        1rem;

    margin:
        0.8rem
        0
        1rem;

    border-left:
        3px solid
        var(--sq-accent);

    border-radius:
        0 10px 10px 0;

    background:
        rgba(
            39,
            194,
            255,
            0.055
        );

    color:
        #abc2d0;

    font-size:
        0.86rem;

    line-height:
        1.55;
}


/* ---------------------------------------------------------
   AI RESPONSE
--------------------------------------------------------- */

.sq-answer-label {
    margin-top:
        0.8rem;

    margin-bottom:
        0.4rem;

    color:
        var(--sq-accent);

    font-size:
        0.72rem;

    font-weight:
        750;

    letter-spacing:
        0.09em;

    text-transform:
        uppercase;
}


/* ---------------------------------------------------------
   FOOTER
--------------------------------------------------------- */

.sq-footer-note {
    margin-top:
        1rem;

    color:
        #6f8b9c;

    font-size:
        0.76rem;
}


/* ---------------------------------------------------------
   RESPONSIVE
--------------------------------------------------------- */

@media (max-width: 900px) {

    .block-container {
        padding-left:
            1rem;

        padding-right:
            1rem;
    }

    .sq-hero {
        padding:
            1.1rem;
    }

    .sq-hero-title {
        font-size:
            1.8rem;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ==========================================================
# HELPERS
# ==========================================================

def render_section_header(
    kicker,
    title,
    description=None,
):
    """
    Render a consistent section heading.
    """

    st.markdown(
        (
            '<div class="sq-section-kicker">'
            f"{kicker}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.subheader(title)

    if description:
        st.caption(description)


def format_window(window):
    """
    Create a readable composite-window description.
    """

    if not window:
        return None

    start = window.get(
        "effective_start"
    )

    end = window.get(
        "effective_end_exclusive"
    )

    if not start or not end:
        return None

    return (
        f"{start} → {end} "
        "(end exclusive)"
    )


# ==========================================================
# SESSION STATE
# ==========================================================

if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None


if "ai_answer" not in st.session_state:
    st.session_state.ai_answer = None


if "ai_answer_source" not in st.session_state:
    st.session_state.ai_answer_source = None


if "ai_status_message" not in st.session_state:
    st.session_state.ai_status_message = None


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:

    st.markdown(
        (
            '<div class="sq-brand">'
            '<div class="sq-brand-mark">◉</div>'
            "<div>"
            '<div class="sq-brand-title">'
            "SETQUERY AI"
            "</div>"
            '<div class="sq-brand-subtitle">'
            "Geospatial Intelligence"
            "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.caption(
        "Satellite-derived land-cover change analysis "
        "using Sentinel-2 and Dynamic World."
    )

    st.divider()

    st.markdown(
        "### New analysis"
    )

    location_name = st.text_input(
        "Location",
        placeholder=(
            "Mumbai, Maharashtra, India"
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

    st.caption(
        "Target dates are the centers of composite "
        "search windows, not exact acquisition dates."
    )

    analyze_clicked = st.button(
        "RUN SATELLITE ANALYSIS",
        type="primary",
        use_container_width=True,
    )

    st.divider()

    st.markdown(
        "#### Analysis method"
    )

    st.markdown(
        (
            '<div class="sq-tag-row">'
            '<span class="sq-tag">'
            "Sentinel-2"
            "</span>"
            '<span class="sq-tag">'
            "Dynamic World ML"
            "</span>"
            '<span class="sq-tag">'
            "60% confidence"
            "</span>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.caption(
        "Measurements are satellite-derived ML "
        "estimates, not surveyed ground truth."
    )


# ==========================================================
# ANALYSIS EXECUTION
# ==========================================================

if analyze_clicked:

    if not location_name.strip():

        st.error(
            "Enter a location before running the analysis."
        )

    else:

        try:

            with st.status(
                "Preparing geospatial analysis...",
                expanded=True,
            ) as status:

                st.write(
                    "Resolving location..."
                )

                geocoder = Nominatim(
                    user_agent=(
                        "setquery-ai-student-project"
                    )
                )

                location_result = (
                    geocoder.geocode(
                        location_name,
                        timeout=10,
                    )
                )

                if location_result is None:

                    raise ValueError(
                        "Location not found. Try a more "
                        "specific place name."
                    )

                latitude = (
                    location_result.latitude
                )

                longitude = (
                    location_result.longitude
                )

                st.write(
                    "Processing Dynamic World "
                    "land-cover probabilities..."
                )

                result = analyze_area(
                    latitude=latitude,
                    longitude=longitude,
                    before_date=str(
                        before_date
                    ),
                    after_date=str(
                        after_date
                    ),
                    radius_km=radius_km,
                    confidence_threshold=(
                        CONFIDENCE_THRESHOLD
                    ),
                )

                st.write(
                    "Building cloud-masked "
                    "Sentinel-2 composites..."
                )

                images = (
                    get_satellite_images(
                        latitude=latitude,
                        longitude=longitude,
                        before_date=str(
                            before_date
                        ),
                        after_date=str(
                            after_date
                        ),
                        radius_km=radius_km,
                    )
                )

                st.write(
                    "Rendering high-confidence "
                    "transition map..."
                )

                change_map = get_change_map(
                    latitude=latitude,
                    longitude=longitude,
                    before_date=str(
                        before_date
                    ),
                    after_date=str(
                        after_date
                    ),
                    radius_km=radius_km,
                    confidence_threshold=(
                        CONFIDENCE_THRESHOLD
                    ),
                )

                st.session_state.analysis_data = {
                    "location":
                        location_result.address,

                    "latitude":
                        latitude,

                    "longitude":
                        longitude,

                    "radius_km":
                        radius_km,

                    "before_date":
                        str(before_date),

                    "after_date":
                        str(after_date),

                    "result":
                        result,

                    "images":
                        images,

                    "change_map":
                        change_map,
                }

                # A new analysis invalidates the old
                # question/answer context.
                st.session_state.ai_answer = None

                st.session_state.ai_answer_source = None

                st.session_state.ai_status_message = None

                status.update(
                    label=(
                        "Analysis completed successfully"
                    ),
                    state="complete",
                    expanded=False,
                )

        except AnalysisValidationError as error:

            st.error(
                f"Invalid analysis request: {error}"
            )

        except AnalysisDataError as error:

            st.error(
                "Satellite analysis could not be "
                f"completed: {error}"
            )

        except ValueError as error:

            st.error(
                str(error)
            )

        except Exception as error:

            st.error(
                "The analysis could not be completed. "
                "An unexpected service or network "
                "error occurred."
            )

            with st.expander(
                "Technical details"
            ):

                st.exception(
                    error
                )


# ==========================================================
# HERO
# ==========================================================

st.markdown(
    (
        '<div class="sq-hero">'
        '<div class="sq-eyebrow">'
        "Satellite Change Intelligence"
        "</div>"
        '<div class="sq-hero-title">'
        "Understand land-cover change from space."
        "</div>"
        '<p class="sq-hero-copy">'
        "Compare satellite-derived land-cover conditions "
        "across two time periods, inspect selected "
        "high-confidence transitions, and ask grounded "
        "questions about the measured results."
        "</p>"
        "</div>"
    ),
    unsafe_allow_html=True,
)


# ==========================================================
# LOAD SAVED ANALYSIS
# ==========================================================

data = (
    st.session_state.analysis_data
)


# ==========================================================
# EMPTY WORKSPACE
# ==========================================================

if data is None:

    render_section_header(
        "Workspace",
        "Start a new analysis",
        (
            "Configure a location and target dates "
            "in the sidebar to generate a "
            "satellite-change analysis."
        ),
    )

    e1, e2, e3 = st.columns(3)

    e1.metric(
        "Satellite source",
        "Sentinel-2",
    )

    e2.metric(
        "Land-cover model",
        "Dynamic World",
    )

    e3.metric(
        "Confidence rule",
        "60%",
    )

    st.info(
        "SetQuery AI is designed for area-level "
        "land-cover patterns. It should not be used "
        "for exact property-level or surveyed "
        "ground-truth claims."
    )

    st.stop()


# ==========================================================
# ANALYSIS DATA
# ==========================================================

location = data["location"]

latitude = data["latitude"]
longitude = data["longitude"]

analyzed_radius = data[
    "radius_km"
]

analyzed_before = data[
    "before_date"
]

analyzed_after = data[
    "after_date"
]

result = data["result"]
images = data["images"]
change_map = data["change_map"]

coverage = result[
    "coverage_percent"
]

coverage_info = (
    get_coverage_interpretation(
        coverage
    )
)

coverage_level = (
    coverage_info["level"]
)

coverage_description = (
    coverage_info["description"]
)


# ==========================================================
# ANALYSIS OVERVIEW
# ==========================================================

render_section_header(
    "Analysis workspace",
    "Study area",
)


st.markdown(
    (
        '<div class="sq-location-card">'
        "<strong>Resolved location</strong>"
        f"{location}"
        "</div>"
    ),
    unsafe_allow_html=True,
)


m1, m2, m3, m4 = (
    st.columns(4)
)


m1.metric(
    "Latitude",
    f"{latitude:.5f}",
)


m2.metric(
    "Longitude",
    f"{longitude:.5f}",
)


m3.metric(
    "Radius",
    f"{analyzed_radius} km",
)


m4.metric(
    "Requested area",
    (
        f"{result['total_area_km2']:.2f} km²"
    ),
)


# ==========================================================
# QUALITY SNAPSHOT
# ==========================================================

st.divider()


render_section_header(
    "Confidence-aware comparison",
    "Analysis quality",
    (
        "Coverage measures the portion of the "
        "requested region that passed the ML "
        "confidence requirement in both periods. "
        "It is not an accuracy score."
    ),
)


q1, q2, q3, q4 = (
    st.columns(4)
)


q1.metric(
    "Comparable coverage",
    f"{coverage:.1f}%",
)


q2.metric(
    "Comparable area",
    (
        f"{result['comparable_area_km2']:.2f} km²"
    ),
)


q3.metric(
    "DW observations · before",
    result[
        "before_observations"
    ],
)


q4.metric(
    "DW observations · after",
    result[
        "after_observations"
    ],
)


if coverage_level == "GOOD":

    st.success(
        "GOOD comparable coverage — "
        f"{coverage_description}"
    )


elif coverage_level == "MODERATE":

    st.warning(
        "MODERATE comparable coverage — "
        f"{coverage_description}"
    )


elif coverage_level == "LIMITED":

    st.warning(
        "LIMITED comparable coverage — "
        f"{coverage_description}"
    )


else:

    st.error(
        "VERY LOW comparable coverage — "
        f"{coverage_description}"
    )


for warning in result.get(
    "warnings",
    [],
):

    st.warning(
        warning
    )


# ==========================================================
# TEMPORAL METADATA
# ==========================================================

before_window = (
    result.get(
        "before_window"
    )
    or images.get(
        "before_window"
    )
)


after_window = (
    result.get(
        "after_window"
    )
    or images.get(
        "after_window"
    )
)


before_window_text = (
    format_window(
        before_window
    )
)


after_window_text = (
    format_window(
        after_window
    )
)


if (
    before_window_text
    or after_window_text
):

    with st.expander(
        "Composite timing details"
    ):

        st.write(
            "The selected dates are target dates. "
            "SetQuery AI builds composites from "
            "observations within surrounding "
            "search windows."
        )

        tc1, tc2 = (
            st.columns(2)
        )

        with tc1:

            st.markdown(
                "**BEFORE target:** "
                f"{analyzed_before}"
            )

            if before_window_text:

                st.code(
                    before_window_text,
                    language=None,
                )

        with tc2:

            st.markdown(
                "**AFTER target:** "
                f"{analyzed_after}"
            )

            if after_window_text:

                st.code(
                    after_window_text,
                    language=None,
                )

        separation = (
            result.get(
                "date_separation_days"
            )
        )

        if separation is not None:

            st.caption(
                "Target-date separation: "
                f"{separation} days."
            )


# ==========================================================
# SENTINEL-2 IMAGERY
# ==========================================================

st.divider()


render_section_header(
    "Sentinel-2",
    "Before / After imagery",
    (
        "Cloud-masked median composites assembled "
        "from observations around each target date."
    ),
)


before_img, after_img = (
    st.columns(2)
)


with before_img:

    st.markdown(
        f"### Before · {analyzed_before}"
    )

    st.image(
        images[
            "before_url"
        ],
        width="stretch",
    )

    st.caption(
        f"{images['before_sentinel_observations']} "
        "Sentinel-2 observations in the composite."
    )


with after_img:

    st.markdown(
        f"### After · {analyzed_after}"
    )

    st.image(
        images[
            "after_url"
        ],
        width="stretch",
    )

    st.caption(
        f"{images['after_sentinel_observations']} "
        "Sentinel-2 observations in the composite."
    )


# ==========================================================
# CHANGE MAP
# ==========================================================

st.divider()


render_section_header(
    "Transition intelligence",
    "High-confidence change map",
    (
        "Selected Dynamic World class transitions "
        "where both periods passed the configured "
        "confidence rule."
    ),
)


st.image(
    change_map[
        "change_url"
    ],
    width="stretch",
)


# IMPORTANT:
# This legend intentionally uses compact HTML.
# Indented HTML can be interpreted by Markdown as code.

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


context_html = (
    '<div class="sq-context">'
    "Change pixels may be enlarged on this "
    "visualization to make small transitions visible. "
    "Numerical area statistics are calculated from "
    "the original classification pixels and are "
    "not enlarged."
    "</div>"
)


st.markdown(
    context_html,
    unsafe_allow_html=True,
)


# ==========================================================
# LAND COVER
# ==========================================================

st.divider()


render_section_header(
    "Measured land cover",
    "Before / After classification",
    (
        "Areas below refer only to pixels included "
        "in the high-confidence comparable subset."
    ),
)


before_col, after_col = (
    st.columns(2)
)


with before_col:

    st.markdown(
        f"### Before · {analyzed_before}"
    )

    lc1, lc2 = (
        st.columns(2)
    )

    lc1.metric(
        "Vegetation",
        (
            f"{result['before_vegetation_km2']:.2f} km²"
        ),
    )

    lc2.metric(
        "Built-up",
        (
            f"{result['before_built_km2']:.2f} km²"
        ),
    )

    lc3, lc4 = (
        st.columns(2)
    )

    lc3.metric(
        "Water",
        (
            f"{result['before_water_km2']:.2f} km²"
        ),
    )

    lc4.metric(
        "Bare ground",
        (
            f"{result['before_bare_km2']:.2f} km²"
        ),
    )


with after_col:

    st.markdown(
        f"### After · {analyzed_after}"
    )

    lc5, lc6 = (
        st.columns(2)
    )

    lc5.metric(
        "Vegetation",
        (
            f"{result['after_vegetation_km2']:.2f} km²"
        ),
    )

    lc6.metric(
        "Built-up",
        (
            f"{result['after_built_km2']:.2f} km²"
        ),
    )

    lc7, lc8 = (
        st.columns(2)
    )

    lc7.metric(
        "Water",
        (
            f"{result['after_water_km2']:.2f} km²"
        ),
    )

    lc8.metric(
        "Bare ground",
        (
            f"{result['after_bare_km2']:.2f} km²"
        ),
    )


# ==========================================================
# NET DIFFERENCE
# ==========================================================

st.divider()


render_section_header(
    "Comparison",
    "Net land-cover difference",
    (
        "Net differences and explicit transitions "
        "are different measurements."
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


bare_change = (
    result[
        "after_bare_km2"
    ]
    -
    result[
        "before_bare_km2"
    ]
)


n1, n2, n3, n4 = (
    st.columns(4)
)


n1.metric(
    "Vegetation",
    (
        f"{vegetation_change:+.3f} km²"
    ),
)


n2.metric(
    "Built-up",
    (
        f"{built_change:+.3f} km²"
    ),
)


n3.metric(
    "Water",
    (
        f"{water_change:+.3f} km²"
    ),
)


n4.metric(
    "Bare ground",
    (
        f"{bare_change:+.3f} km²"
    ),
)


st.caption(
    "Net differences apply only to the "
    "high-confidence comparable subset."
)


# ==========================================================
# TRANSITIONS
# ==========================================================

st.divider()


render_section_header(
    "Change matrix",
    "Detected transitions",
    (
        "These measurements represent selected "
        "explicit before-to-after class transitions."
    ),
)


t1, t2, t3 = (
    st.columns(3)
)


t1.metric(
    "Vegetation → Built-up",
    (
        f"{result['vegetation_to_built_km2']:.4f} km²"
    ),
)


t2.metric(
    "Built-up → Vegetation",
    (
        f"{result['built_to_vegetation_km2']:.4f} km²"
    ),
)


t3.metric(
    "Bare → Built-up",
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


# ==========================================================
# DETERMINISTIC ANALYSIS
# ==========================================================

st.divider()


render_section_header(
    "Grounded interpretation",
    "SetQuery AI analysis",
    (
        "Generated deterministically from the "
        "measured satellite and Dynamic World results."
    ),
)


summary = (
    generate_analysis_summary(
        location=location,
        before_date=analyzed_before,
        after_date=analyzed_after,
        result=result,
    )
)


st.info(
    summary
)


# ==========================================================
# ASK SETQUERY AI
# ==========================================================

st.divider()


render_section_header(
    "Grounded Q&A",
    "Ask SetQuery AI",
    (
        "Gemini receives only the structured analysis "
        "measurements plus your question. If Gemini is "
        "unavailable, SetQuery AI uses its deterministic "
        "local fallback."
    ),
)


with st.form(
    "analysis_question_form",
    clear_on_submit=False,
):

    user_question = (
        st.text_input(
            "Question about this analysis",
            placeholder=(
                "e.g. How did built-up land change?"
            ),
        )
    )

    ask_clicked = (
        st.form_submit_button(
            "ASK SETQUERY AI",
            type="primary",
            use_container_width=True,
        )
    )


if ask_clicked:

    if not user_question.strip():

        st.warning(
            "Enter a question about the "
            "completed analysis."
        )

    else:

        with st.spinner(
            "Generating a grounded answer..."
        ):

            try:

                answer = ask_gemini(
                    question=(
                        user_question
                    ),
                    result=result,
                    location=location,
                    before_date=(
                        analyzed_before
                    ),
                    after_date=(
                        analyzed_after
                    ),
                )

                st.session_state.ai_answer = (
                    answer
                )

                st.session_state.ai_answer_source = (
                    "gemini"
                )

                st.session_state.ai_status_message = (
                    None
                )

            except (
                LLMUnavailableError,
                LLMConfigurationError,
            ) as error:

                answer = answer_query(
                    user_question,
                    result,
                )

                st.session_state.ai_answer = (
                    answer
                )

                st.session_state.ai_answer_source = (
                    "fallback"
                )

                st.session_state.ai_status_message = (
                    str(error)
                )

            except Exception as error:

                answer = answer_query(
                    user_question,
                    result,
                )

                st.session_state.ai_answer = (
                    answer
                )

                st.session_state.ai_answer_source = (
                    "fallback-error"
                )

                st.session_state.ai_status_message = (
                    str(error)
                )


# ==========================================================
# AI RESPONSE DISPLAY
# ==========================================================

if st.session_state.ai_answer:

    source = (
        st.session_state.ai_answer_source
    )

    if source == "gemini":

        st.success(
            "Gemini grounded response"
        )

    elif source == "fallback":

        st.warning(
            "Gemini is unavailable. Showing the "
            "deterministic grounded fallback response."
        )

        if (
            st.session_state.ai_status_message
        ):

            st.caption(
                "AI service status: "
                f"{st.session_state.ai_status_message}"
            )

    else:

        st.warning(
            "The AI service encountered an unexpected "
            "error. Showing the deterministic grounded "
            "fallback response."
        )

    st.markdown(
        (
            '<div class="sq-answer-label">'
            "SetQuery response"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.write(
        st.session_state.ai_answer
    )


# ==========================================================
# METHODOLOGY / LIMITATIONS
# ==========================================================

st.divider()


render_section_header(
    "Methodology",
    "Interpretation boundaries",
)


with st.expander(
    "Data sources, confidence and limitations"
):

    st.markdown(
        """
- Sentinel-2 is used for cloud-masked true-color
  composite imagery.

- Google's Dynamic World machine-learning dataset is
  used for land-cover probabilities and classification.

- A pixel enters the high-confidence comparison only
  when both periods meet the configured 60% confidence
  threshold.

- Comparable coverage is not classification accuracy.

- Selected dates are target dates at the center of
  composite search windows; they are not necessarily
  satellite acquisition dates.

- Transition-map pixels can be visually enlarged, but
  numerical statistics use the original pixels.

- Results are satellite-derived ML estimates rather than
  surveyed ground truth.

- The system is intended for area-level patterns. It
  should not claim reliable detection of individual
  houses, individual trees, tiny roads, exact
  property-level change, or causes of change.
"""
    )


st.markdown(
    (
        '<div class="sq-footer-note">'
        "SETQUERY AI · Satellite change detection "
        "and grounded analysis · "
        "Sentinel-2 + Dynamic World"
        "</div>"
    ),
    unsafe_allow_html=True,
)