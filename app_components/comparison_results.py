"""Modern and historical comparison result rendering for SetQuery AI."""

import streamlit as st
from ui import (
    section, sensor_text, render_status, render_legend,
    metric_grid, render_before_after_compare,
    build_study_area_map, modern_land_cover_chart,
    historical_index_chart, render_burn_evidence_tab,
    render_vegetation_stress_tab, render_flood_evidence_tab,
    render_ai_qa_section,
)
from report import generate_analysis_summary, get_coverage_interpretation
from historical_report import (
    generate_historical_summary,
    get_historical_coverage_level,
    get_historical_source_support,
    get_historical_support_warnings,
)

def render_comparison_results(data, change_legend):
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
            render_legend(change_legend)
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
