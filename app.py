import streamlit as st
from geopy.geocoders import Nominatim
from datetime import date

from analysis import (
    analyze_area,
    get_satellite_images,
    get_change_map,
)

from report import generate_analysis_summary
from query import answer_query
from llm import ask_gemini


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="SetQuery AI",
    page_icon="🛰️",
    layout="wide",
)

st.title("🛰️ SetQuery AI")
st.subheader("Satellite Change Detection & AI Analysis")

st.write(
    "Analyze land-cover changes between two dates "
    "using Sentinel-2 satellite imagery and "
    "machine-learning land-cover data."
)

st.divider()


# =====================================================
# SESSION STATE
# =====================================================

if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None


# =====================================================
# INPUTS
# =====================================================

location_name = st.text_input(
    "Location",
    placeholder="e.g. Mumbai, Maharashtra, India",
)

date_col1, date_col2 = st.columns(2)

with date_col1:
    before_date = st.date_input(
        "Before date",
        value=date(2022, 9, 15),
    )

with date_col2:
    after_date = st.date_input(
        "After date",
        value=date(2025, 9, 15),
    )


radius_km = st.slider(
    "Analysis radius (km)",
    min_value=1,
    max_value=20,
    value=10,
)

confidence = 0.60


# =====================================================
# ANALYZE BUTTON
# =====================================================

if st.button(
    "Analyze Area",
    type="primary",
):

    if not location_name.strip():

        st.error(
            "Please enter a location."
        )

    elif before_date >= after_date:

        st.error(
            "Before date must be earlier than after date."
        )

    else:

        try:

            # =========================================
            # GEOCODING
            # =========================================

            with st.spinner(
                "Finding location..."
            ):

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

                st.error(
                    "Location not found. "
                    "Try a more specific place name."
                )

                st.stop()


            latitude = location_result.latitude
            longitude = location_result.longitude


            # =========================================
            # EARTH ENGINE
            # =========================================

            with st.spinner(
                "Analyzing satellite and "
                "land-cover data..."
            ):

                result = analyze_area(
                    latitude=latitude,
                    longitude=longitude,
                    before_date=str(before_date),
                    after_date=str(after_date),
                    radius_km=radius_km,
                    confidence_threshold=confidence,
                )

                images = get_satellite_images(
                    latitude=latitude,
                    longitude=longitude,
                    before_date=str(before_date),
                    after_date=str(after_date),
                    radius_km=radius_km,
                )

                change_map = get_change_map(
                    latitude=latitude,
                    longitude=longitude,
                    before_date=str(before_date),
                    after_date=str(after_date),
                    radius_km=radius_km,
                    confidence_threshold=confidence,
                )


            # =========================================
            # SAVE RESULTS
            # =========================================

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


            st.success(
                "Analysis completed successfully."
            )


        except Exception as error:

            st.error(
                "Analysis failed."
            )

            st.exception(
                error
            )


# =====================================================
# LOAD SAVED ANALYSIS
# =====================================================

data = st.session_state.analysis_data


# =====================================================
# DISPLAY RESULTS
# =====================================================

if data is not None:

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


    # =================================================
    # LOCATION
    # =================================================

    st.divider()

    st.subheader(
        "📍 Analysis Location"
    )

    st.write(
        location
    )


    a, b, c = st.columns(3)


    a.metric(
        "Latitude",
        f"{latitude:.5f}",
    )


    b.metric(
        "Longitude",
        f"{longitude:.5f}",
    )


    c.metric(
        "Radius",
        f"{analyzed_radius} km",
    )


    # =================================================
    # SATELLITE IMAGES
    # =================================================

    st.divider()

    st.subheader(
        "🛰️ Before & After Satellite Imagery"
    )

    st.caption(
        "Cloud-masked Sentinel-2 composites "
        "created from observations around each "
        "selected date."
    )


    before_img, after_img = (
        st.columns(2)
    )


    with before_img:

        st.markdown(
            f"### Before — {analyzed_before}"
        )

        st.image(
            images["before_url"],
            width="stretch",
        )

        st.caption(
            "Sentinel-2 observations used: "
            f"{images['before_sentinel_observations']}"
        )


    with after_img:

        st.markdown(
            f"### After — {analyzed_after}"
        )

        st.image(
            images["after_url"],
            width="stretch",
        )

        st.caption(
            "Sentinel-2 observations used: "
            f"{images['after_sentinel_observations']}"
        )


    # =================================================
    # CHANGE MAP
    # =================================================

    st.divider()

    st.subheader(
        "🗺️ High-Confidence Change Map"
    )

    st.write(
        "Highlighted regions show selected "
        "land-cover transitions detected with "
        "sufficient confidence in both periods."
    )


    st.image(
        change_map["change_url"],
        width="stretch",
    )


    st.markdown(
        """
### Change Map Legend

🔴 **Red** — Vegetation → Built-up  
🟢 **Green** — Built-up → Vegetation  
🟡 **Yellow** — Bare ground → Built-up  
🔵 **Blue** — Non-water → Water  
🟠 **Orange** — Water → Non-water
"""
    )


    st.caption(
        "Colored change pixels may be enlarged "
        "for visibility. Numerical area statistics "
        "are calculated from the original "
        "classification pixels."
    )


    # =================================================
    # DATA QUALITY
    # =================================================

    st.divider()

    st.subheader(
        "📡 Data Quality"
    )


    coverage = result[
        "coverage_percent"
    ]


    q1, q2, q3 = st.columns(3)


    q1.metric(
        "ML observations before",
        result[
            "before_observations"
        ],
    )


    q2.metric(
        "ML observations after",
        result[
            "after_observations"
        ],
    )


    q3.metric(
        "Comparable coverage",
        f"{coverage:.1f}%",
    )


    if coverage >= 70:

        st.success(
            "Data quality: GOOD — a large "
            "portion of the selected region "
            "passed the confidence threshold."
        )

    elif coverage >= 40:

        st.warning(
            "Data quality: MODERATE — only "
            "part of the selected region passed "
            "the confidence threshold."
        )

    else:

        st.error(
            "Data quality: LOW — results "
            "should be interpreted cautiously."
        )


    st.caption(
        "Coverage is not an accuracy percentage. "
        "It represents the portion of the study "
        "area meeting the 60% ML confidence "
        "threshold in both periods."
    )


    # =================================================
    # LAND COVER
    # =================================================

    st.divider()

    st.subheader(
        "🌍 Land-Cover Analysis"
    )


    before_col, after_col = (
        st.columns(2)
    )


    with before_col:

        st.markdown(
            f"### Before — {analyzed_before}"
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


    with after_col:

        st.markdown(
            f"### After — {analyzed_after}"
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


    # =================================================
    # NET DIFFERENCE
    # =================================================

    st.divider()

    st.subheader(
        "📈 Net Land-Cover Difference"
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


    n1, n2, n3 = st.columns(3)


    n1.metric(
        "Vegetation",
        f"{vegetation_change:+.3f} km²",
    )


    n2.metric(
        "Built-up",
        f"{built_change:+.3f} km²",
    )


    n3.metric(
        "Water",
        f"{water_change:+.3f} km²",
    )


    st.caption(
        "Net differences apply only to "
        "high-confidence comparable pixels."
    )


    # =================================================
    # TRANSITIONS
    # =================================================

    st.divider()

    st.subheader(
        "🔄 High-Confidence Transitions"
    )


    t1, t2, t3 = st.columns(3)


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


    t4, t5 = st.columns(2)


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


    # =================================================
    # AUTOMATIC SUMMARY
    # =================================================

    st.divider()

    st.subheader(
        "🤖 SetQuery AI Analysis"
    )


    summary = (
        generate_analysis_summary(
            location=location,
            before_date=analyzed_before,
            after_date=analyzed_after,
            result=result,
        )
    )


    st.write(
        summary
    )


    st.caption(
        "This summary is generated directly "
        "from the measured satellite/ML results."
    )


    # =================================================
    # QUERY SYSTEM
    # =================================================

    st.markdown(
        "### 💬 Ask SetQuery AI"
    )


    user_question = st.text_input(
        "Ask a question about this analysis",
        placeholder=(
            "e.g. Did built-up land increase?"
        ),
        key="analysis_question",
    )


    if user_question:

        with st.spinner(
            "SetQuery AI is analyzing your question..."
        ):

            try:

                answer = ask_gemini(
                    question=user_question,
                    result=result,
                    location=location,
                    before_date=analyzed_before,
                    after_date=analyzed_after,
                )

                st.success(
                    "AI-powered answer"
                )

            except Exception as error:

                answer = answer_query(
                    user_question,
                    result,
                )

                st.warning(
                    "Gemini is temporarily unavailable. "
                    "Showing a grounded fallback answer."
                )

                st.error(
                    f"Gemini error: {error}"
                )


    # =================================================
    # COVERAGE
    # =================================================

    st.divider()

    st.subheader(
        "📊 Analysis Coverage"
    )


    c1, c2, c3 = st.columns(3)


    c1.metric(
        "Requested area",
        (
            f"{result['total_area_km2']:.2f} km²"
        ),
    )


    c2.metric(
        "Comparable area",
        (
            f"{result['comparable_area_km2']:.2f} km²"
        ),
    )


    c3.metric(
        "Coverage",
        f"{coverage:.1f}%",
    )


    st.info(
        "Results are satellite-derived "
        "machine-learning estimates, not surveyed "
        "ground truth. Cloud cover, seasonality, "
        "satellite resolution and model confidence "
        "can influence the measurements."
    )