import streamlit as st
from geopy.geocoders import Nominatim
from datetime import date

from analysis import (
    analyze_area,
    get_satellite_images
)


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="SetQuery AI",
    page_icon="🛰️",
    layout="wide"
)

st.title("🛰️ SetQuery AI")

st.subheader(
    "Satellite Change Detection & AI Analysis"
)

st.write(
    "Analyze land-cover changes between two dates "
    "using Sentinel-2 satellite imagery and "
    "machine-learning land-cover data."
)

st.divider()


# =====================================================
# USER INPUTS
# =====================================================

location_name = st.text_input(
    "Location",
    placeholder="e.g. Mumbai, Maharashtra, India"
)

date_col1, date_col2 = st.columns(2)

with date_col1:
    before_date = st.date_input(
        "Before date",
        value=date(2022, 9, 15)
    )

with date_col2:
    after_date = st.date_input(
        "After date",
        value=date(2025, 9, 15)
    )


radius_km = st.slider(
    "Analysis radius (km)",
    min_value=1,
    max_value=20,
    value=10
)


# Fixed for our current V4 analysis
confidence = 0.60


# =====================================================
# ANALYZE
# =====================================================

if st.button(
    "Analyze Area",
    type="primary"
):

    # -------------------------------------------------
    # INPUT VALIDATION
    # -------------------------------------------------

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
            # FIND LOCATION
            # =========================================

            with st.spinner(
                "Finding location..."
            ):

                geocoder = Nominatim(
                    user_agent=(
                        "setquery-ai-student-project"
                    )
                )

                location = geocoder.geocode(
                    location_name,
                    timeout=10
                )


            if location is None:

                st.error(
                    "Location not found. "
                    "Try a more specific place name."
                )

                st.stop()


            latitude = location.latitude
            longitude = location.longitude


            st.success(
                f"Location found: {location.address}"
            )


            # =========================================
            # EARTH ENGINE ANALYSIS
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
                    confidence_threshold=confidence
                )


                images = get_satellite_images(
                    latitude=latitude,
                    longitude=longitude,
                    before_date=str(before_date),
                    after_date=str(after_date),
                    radius_km=radius_km
                )


            # =========================================
            # LOCATION
            # =========================================

            st.subheader(
                "📍 Analysis Location"
            )

            st.write(
                location.address
            )

            a, b, c = st.columns(3)

            a.metric(
                "Latitude",
                f"{latitude:.5f}"
            )

            b.metric(
                "Longitude",
                f"{longitude:.5f}"
            )

            c.metric(
                "Radius",
                f"{radius_km} km"
            )


            st.divider()


            # =========================================
            # BEFORE / AFTER SATELLITE IMAGERY
            # =========================================

            st.subheader(
                "🛰️ Before & After Satellite Imagery"
            )

            st.caption(
                "Cloud-masked Sentinel-2 composites "
                "created from observations around each "
                "selected date."
            )


            before_img, after_img = st.columns(2)


            with before_img:

                st.markdown(
                    f"### Before — {before_date}"
                )

                st.image(
                    images["before_url"],
                    width="stretch"
                )

                st.caption(
                    "Satellite composite centered around "
                    f"{before_date}"
                )

                st.caption(
                    "Sentinel-2 observations used: "
                    f"{images['before_sentinel_observations']}"
                )


            with after_img:

                st.markdown(
                    f"### After — {after_date}"
                )

                st.image(
                    images["after_url"],
                    width="stretch"
                )

                st.caption(
                    "Satellite composite centered around "
                    f"{after_date}"
                )

                st.caption(
                    "Sentinel-2 observations used: "
                    f"{images['after_sentinel_observations']}"
                )


            st.divider()


            # =========================================
            # DATA QUALITY
            # =========================================

            st.subheader(
                "📡 Data Quality"
            )

            q1, q2, q3 = st.columns(3)


            q1.metric(
                "ML observations before",
                result[
                    "before_observations"
                ]
            )


            q2.metric(
                "ML observations after",
                result[
                    "after_observations"
                ]
            )


            coverage = result[
                "coverage_percent"
            ]


            q3.metric(
                "Comparable coverage",
                f"{coverage:.1f}%"
            )


            # -----------------------------------------
            # QUALITY MESSAGE
            # -----------------------------------------

            if coverage >= 70:

                st.success(
                    "Data quality: GOOD — a large portion "
                    "of the selected region passed the "
                    "high-confidence comparison threshold."
                )

            elif coverage >= 40:

                st.warning(
                    "Data quality: MODERATE — only part "
                    "of the selected region passed the "
                    "high-confidence comparison threshold."
                )

            else:

                st.error(
                    "Data quality: LOW — results should "
                    "be interpreted cautiously because "
                    "high-confidence comparable coverage "
                    "is limited."
                )


            st.caption(
                "Only pixels meeting the 60% ML "
                "confidence threshold in BOTH periods "
                "are included in high-confidence "
                "land-cover statistics."
            )


            st.divider()


            # =========================================
            # LAND COVER
            # =========================================

            st.subheader(
                "🌍 Land-Cover Analysis"
            )


            before_col, after_col = (
                st.columns(2)
            )


            with before_col:

                st.markdown(
                    f"### Before — {before_date}"
                )


                st.metric(
                    "Vegetation",
                    f"{result['before_vegetation_km2']:.2f} km²"
                )


                st.metric(
                    "Built-up",
                    f"{result['before_built_km2']:.2f} km²"
                )


                st.metric(
                    "Water",
                    f"{result['before_water_km2']:.2f} km²"
                )


                st.metric(
                    "Bare ground",
                    f"{result['before_bare_km2']:.2f} km²"
                )


            with after_col:

                st.markdown(
                    f"### After — {after_date}"
                )


                st.metric(
                    "Vegetation",
                    f"{result['after_vegetation_km2']:.2f} km²"
                )


                st.metric(
                    "Built-up",
                    f"{result['after_built_km2']:.2f} km²"
                )


                st.metric(
                    "Water",
                    f"{result['after_water_km2']:.2f} km²"
                )


                st.metric(
                    "Bare ground",
                    f"{result['after_bare_km2']:.2f} km²"
                )


            st.divider()


            # =========================================
            # CHANGE SUMMARY
            # =========================================

            st.subheader(
                "📈 Net Land-Cover Difference"
            )


            vegetation_change = (
                result["after_vegetation_km2"]
                - result["before_vegetation_km2"]
            )


            built_change = (
                result["after_built_km2"]
                - result["before_built_km2"]
            )


            water_change = (
                result["after_water_km2"]
                - result["before_water_km2"]
            )


            n1, n2, n3 = st.columns(3)


            n1.metric(
                "Vegetation",
                f"{vegetation_change:+.3f} km²"
            )


            n2.metric(
                "Built-up",
                f"{built_change:+.3f} km²"
            )


            n3.metric(
                "Water",
                f"{water_change:+.3f} km²"
            )


            st.caption(
                "Net differences describe ML-classified "
                "high-confidence comparable pixels. "
                "They do not automatically imply a "
                "permanent physical land conversion."
            )


            st.divider()


            # =========================================
            # DETECTED TRANSITIONS
            # =========================================

            st.subheader(
                "🔄 High-Confidence Transitions"
            )


            t1, t2, t3 = st.columns(3)


            t1.metric(
                "Vegetation → Built-up",
                (
                    f"{result['vegetation_to_built_km2']:.4f} km²"
                )
            )


            t2.metric(
                "Built-up → Vegetation",
                (
                    f"{result['built_to_vegetation_km2']:.4f} km²"
                )
            )


            t3.metric(
                "Bare → Built-up",
                (
                    f"{result['bare_to_built_km2']:.4f} km²"
                )
            )


            t4, t5 = st.columns(2)


            t4.metric(
                "Water → Non-water",
                (
                    f"{result['water_to_nonwater_km2']:.4f} km²"
                )
            )


            t5.metric(
                "Non-water → Water",
                (
                    f"{result['nonwater_to_water_km2']:.4f} km²"
                )
            )


            st.divider()


            # =========================================
            # COVERAGE INFORMATION
            # =========================================

            st.subheader(
                "📊 Analysis Coverage"
            )


            c1, c2, c3 = st.columns(3)


            c1.metric(
                "Requested area",
                (
                    f"{result['total_area_km2']:.2f} km²"
                )
            )


            c2.metric(
                "Comparable area",
                (
                    f"{result['comparable_area_km2']:.2f} km²"
                )
            )


            c3.metric(
                "Coverage",
                f"{coverage:.1f}%"
            )


            st.info(
                "Results are satellite-derived "
                "machine-learning estimates, not "
                "surveyed ground truth. Cloud cover, "
                "seasonal conditions, model confidence "
                "and satellite resolution can affect "
                "the analysis."
            )


        except Exception as error:

            st.error(
                "Analysis failed."
            )

            st.exception(error)