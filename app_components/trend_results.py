"""Trend analysis result rendering for SetQuery AI."""

import streamlit as st
from ui import section, build_study_area_map, trend_composition_chart, metric_grid

def render_trend_results(trend_data):
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
