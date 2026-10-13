from analysis import prepare_modern_analysis
"""
Streamlit fragments for on-demand analysis (Burn, Vegetation, Flood, AI).
"""

import time
import streamlit as st
import altair as alt
from .helpers import metric_grid


@st.fragment
def render_burn_evidence_tab(latitude, longitude, before, after, radius):
    """Render burn evidence (NBR/dNBR), computed on demand."""
    burn_evidence = st.session_state.burn_evidence_data
    burn_error = st.session_state.burn_evidence_error

    if burn_evidence is None:
        st.info(
            "Burn evidence is not calculated automatically because "
            "it uses additional spectral analysis and adds noticeable "
            "extra time. Click below to check this specific area and "
            "date range."
        )

        if burn_error:
            st.warning(burn_error)

        if st.button("Check burn evidence (NBR/dNBR, ~5-10s)", key="check_burn_evidence_button"):
            try:
                from burn_analysis import analyze_burn_evidence
                with st.spinner("Calculating burn evidence..."):
                    burn_start_time = time.perf_counter()
                    burn_context = prepare_modern_analysis(
                        latitude=latitude,
                        longitude=longitude,
                        before_date=before,
                        after_date=after,
                        radius_km=radius,
                    )
                    burn_evidence = analyze_burn_evidence(burn_context)
                    burn_elapsed = time.perf_counter() - burn_start_time

                print(f"SetQuery burn evidence analysis: {burn_elapsed:.1f} seconds")

                st.session_state.burn_evidence_data = burn_evidence
                st.session_state.burn_evidence_error = None
                st.rerun(scope="fragment")

            except Exception as error:
                st.session_state.burn_evidence_error = f"Burn evidence could not be calculated: {error}"
                st.rerun(scope="fragment")

    if burn_evidence:
        st.caption("Spectral evidence from NBR/dNBR, not a validated fire detection or damage assessment.")

        metric_grid(
            [
                ("Before mean NBR", f"{burn_evidence['before_mean_nbr']:.3f}"),
                ("After mean NBR", f"{burn_evidence['after_mean_nbr']:.3f}"),
                ("Mean dNBR", f"{burn_evidence['mean_dnbr']:+.3f}"),
            ],
            per_row=3,
        )

        severity_rows = [
            {"Category": label.replace("_", " ").title(), "Area": area_km2}
            for label, area_km2 in burn_evidence["severity_area_km2"].items()
        ]

        severity_chart = (
            alt.Chart(alt.Data(values=severity_rows))
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#ff9f0a")
            .encode(
                x=alt.X("Category:N", title=None, sort=None),
                y=alt.Y("Area:Q", title="Area (km²)"),
                tooltip=[alt.Tooltip("Category:N"), alt.Tooltip("Area:Q", format=".4f")],
            )
            .properties(height=250)
            .configure_view(strokeOpacity=0)
            .configure_axis(labelColor="#86868b", titleColor="#86868b", gridColor="#1c1c1e", domainColor="#2c2c2e", tickColor="#2c2c2e")
        )

        st.altair_chart(severity_chart, width="stretch")
        st.caption(burn_evidence["severity_thresholds_note"])

        for warning in burn_evidence.get("warnings", []):
            st.warning(warning)


@st.fragment
def render_vegetation_stress_tab(latitude, longitude, before, after, radius):
    """Render vegetation stress (NDVI change), computed on demand."""
    vegetation_stress = st.session_state.vegetation_stress_data
    vegetation_error = st.session_state.vegetation_stress_error

    if vegetation_stress is None:
        st.info(
            "Vegetation stress is not calculated automatically because "
            "it uses additional spectral analysis and adds noticeable "
            "extra time. Click below to check this specific area and "
            "date range."
        )

        if vegetation_error:
            st.warning(vegetation_error)

        if st.button("Check vegetation stress (NDVI change, ~5-10s)", key="check_vegetation_stress_button"):
            try:
                from vegetation_stress_analysis import analyze_vegetation_stress
                with st.spinner("Calculating vegetation stress..."):
                    veg_start_time = time.perf_counter()
                    veg_context = prepare_modern_analysis(
                        latitude=latitude,
                        longitude=longitude,
                        before_date=before,
                        after_date=after,
                        radius_km=radius,
                    )
                    vegetation_stress = analyze_vegetation_stress(veg_context)
                    veg_elapsed = time.perf_counter() - veg_start_time

                print(f"SetQuery vegetation stress analysis: {veg_elapsed:.1f} seconds")

                st.session_state.vegetation_stress_data = vegetation_stress
                st.session_state.vegetation_stress_error = None
                st.rerun(scope="fragment")

            except Exception as error:
                st.session_state.vegetation_stress_error = f"Vegetation stress could not be calculated: {error}"
                st.rerun(scope="fragment")

    if vegetation_stress:
        st.caption("Spectral evidence from NDVI change, not a validated drought or crop-stress confirmation.")

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
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#30d158")
            .encode(
                x=alt.X("Category:N", title=None, sort=None),
                y=alt.Y("Percent:Q", title="% of valid area"),
                tooltip=[alt.Tooltip("Category:N"), alt.Tooltip("Percent:Q", format=".2f")],
            )
            .properties(height=250)
            .configure_view(strokeOpacity=0)
            .configure_axis(labelColor="#86868b", titleColor="#86868b", gridColor="#1c1c1e", domainColor="#2c2c2e", tickColor="#2c2c2e")
        )

        st.altair_chart(breakdown_chart, width="stretch")

        for warning in vegetation_stress.get("warnings", []):
            st.warning(warning)


@st.fragment
def render_flood_evidence_tab(latitude, longitude, before, after, radius):
    """Render flood evidence (Sentinel-1 SAR), computed on demand."""
    st.caption("SAR-based surface-water change indicator, not a validated flood damage assessment.")

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

        if st.button("Check flood evidence (Sentinel-1 SAR, ~10-20s)", key="check_flood_evidence_button"):
            try:
                from flood_analysis import analyze_flood_evidence
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

                print(f"SetQuery flood evidence analysis: {flood_elapsed:.1f} seconds")

                st.session_state.flood_evidence_data = flood_result
                st.session_state.flood_evidence_error = None
                st.rerun(scope="fragment")

            except Exception as error:
                st.session_state.flood_evidence_error = f"Flood evidence could not be calculated: {error}"
                st.rerun(scope="fragment")

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


def resolve_ai_answer(mode, question, result, location, before, after):
    """Answer a question using Gemini, falling back to local measurements."""
    from llm import ask_gemini, ask_gemini_historical, LLMUnavailableError, LLMConfigurationError
    from query import answer_query
    from historical_report import answer_historical_query

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


@st.fragment
def render_ai_qa_section(mode, result, location, before, after):
    """Render the Ask SetQuery AI popover + answer."""
    AI_SOURCE_CAPTIONS = {
        "gemini": "Generated from the current analysis measurements",
        "gemini-historical": "Generated from the current analysis measurements",
        "historical-local": "Local response from historical analysis measurements",
        "fallback": "Local response from analysis measurements",
    }

    with st.popover("Ask SetQuery AI", use_container_width=False):
        with st.form("question_form", clear_on_submit=False):
            question = st.text_input(
                "Question",
                placeholder="What changed in this area?",
                label_visibility="collapsed",
            )
            ask_clicked = st.form_submit_button("Ask", type="primary", use_container_width=True)

        if ask_clicked and question.strip():
            answer, source, status = resolve_ai_answer(mode, question, result, location, before, after)
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