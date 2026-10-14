"""Professional SetQuery PDF report workspace."""

import base64

from report_export_staging.cache_safety import (
    report_fingerprint,
    trend_fingerprint,
)

import streamlit as st

from report_export_staging.evidence import collect_selected_evidence
from report_export_staging.ai_interpretation import generate_report_interpretation
from report_export_staging.real_pdf_builder import generate_real_report
from report_export_staging.evidence_cache import (
    get_cached_evidence,
    store_cached_evidence,
)





def render_print_option(pdf_bytes, key):
    """
    Display the generated PDF inside the application.

    Uses existing PDF bytes only.
    No satellite analysis or PDF regeneration occurs.
    """

    import base64

    if not pdf_bytes:
        return

    size_mb = len(pdf_bytes) / (1024 * 1024)

    with st.expander("Preview and print report", expanded=False):

        if size_mb > 12:
            st.warning(
                "This report is large and may not preview "
                "reliably in the browser. Please download "
                "the PDF and print it from your PDF viewer."
            )
            return

        encoded = base64.b64encode(pdf_bytes).decode("ascii")

        st.markdown(
            f"""
            <iframe
                src="data:application/pdf;base64,{encoded}"
                width="100%"
                height="700"
                style="border:1px solid #E4E7EC;border-radius:8px;"
            ></iframe>
            """,
            unsafe_allow_html=True,
        )

        st.caption(
            "Use your browser or PDF viewer print option "
            "(Ctrl+P) to print this report. If the preview "
            "does not load, download the PDF instead."
        )


def render_report_workspace():

    st.markdown("## Analysis Reports")
    st.caption(
        "Generate a professional satellite analysis report "
        "using the current measurements."
    )

    analysis_data = st.session_state.get("analysis_data")


    # Trend reports use their own six-page renderer.
    trend_data = st.session_state.get("trend_data")

    if analysis_data is None and trend_data is not None:
        from report_export_staging.trend_pdf_builder import (
            generate_trend_report,
        )

        st.markdown("### Current Trend Analysis")
        st.caption(
            f'{trend_data["location"]} | '
            f'{len(trend_data["periods"])} time points'
        )

        current_trend_fingerprint = trend_fingerprint(
            trend_data
        )

        if (
            st.session_state.get("trend_report_fingerprint")
            != current_trend_fingerprint
        ):
            st.session_state.trend_report_pdf = None

        if st.button(
            "Generate Trend PDF Report",
            type="primary",
            use_container_width=True,
            key="generate_trend_report",
        ):
            st.session_state.trend_report_pdf = None
            st.session_state.trend_report_fingerprint = None

            try:
                with st.status(
                    "Preparing trend report...",
                    expanded=True,
                ) as status:

                    def progress(message):
                        st.write(message)

                    pdf_bytes = generate_trend_report(
                        trend_data,
                        progress=progress,
                    )

                    st.session_state.trend_report_pdf = pdf_bytes
                    st.session_state.trend_report_fingerprint = (
                        current_trend_fingerprint
                    )

                    status.update(
                        label="Trend report ready",
                        state="complete",
                        expanded=False,
                    )

            except Exception as error:
                st.error("Trend report generation failed.")
                with st.expander("Technical details"):
                    st.exception(error)

        pdf_bytes = st.session_state.get("trend_report_pdf")

        if pdf_bytes:
            st.download_button(
                "Download Trend PDF",
                data=pdf_bytes,
                file_name="SetQuery_Trend_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

            render_print_option(
                pdf_bytes,
                key="trend_print",
            )

        return

    if not analysis_data:
        st.info(
            "Run a satellite comparison first to prepare "
            "a report."
        )
        return

    mode = analysis_data["mode"]

    st.markdown("### Current Analysis")

    a, b, c = st.columns(3)

    with a:
        st.metric("Analysis mode", analysis_data["mode_label"])

    with b:
        st.metric("Radius", f'{analysis_data["radius_km"]} km')

    with c:
        st.metric(
            "Coverage",
            f'{analysis_data["result"]["coverage_percent"]:.1f}%',
        )

    st.caption(
        f'{analysis_data["location"]} | '
        f'{analysis_data["before_date"]} to '
        f'{analysis_data["after_date"]}'
    )

    st.divider()

    st.markdown("### Report Configuration")

    preset = st.segmented_control(
        "Report type",
        ["Standard", "Detailed"],
        default="Standard",
    )

    st.markdown("#### Report Contents")
    st.checkbox("Study area and reference map", value=True, disabled=True)
    st.checkbox("Before/After satellite imagery", value=True, disabled=True)
    st.checkbox("Change detection or spectral comparison", value=True, disabled=True)
    st.checkbox("Statistics and charts", value=True, disabled=True)
    st.checkbox("Methodology and limitations", value=True, disabled=True)

    selected = []

    if mode == "modern_ml":

        st.markdown("#### Optional Evidence")

        burn = st.checkbox(
            "Burn Evidence (NBR/dNBR)",
            value=False,
        )

        vegetation = st.checkbox(
            "Vegetation Stress (NDVI)",
            value=False,
        )

        flood = st.checkbox(
            "Flood Evidence (Sentinel-1 SAR)",
            value=False,
        )

        if burn:
            selected.append("burn")

        if vegetation:
            selected.append("vegetation")

        if flood:
            selected.append("flood")

    else:
        st.caption(
            "Supplementary evidence is currently available "
            "for Modern ML reports."
        )

    st.markdown("#### AI Interpretation")

    include_ai = st.checkbox(
        "Include AI-generated interpretation",
        value=False,
        help=(
            "Optional Gemini explanation grounded in current "
            "measurements. A deterministic summary is used "
            "if Gemini is unavailable."
        ),
    )

    st.divider()

    fingerprint = report_fingerprint(
        analysis_data,
        preset=preset,
        selected=selected,
        include_ai=include_ai,
    )

    if st.session_state.get("report_fingerprint") != fingerprint:
        st.session_state.report_pdf = None

    if st.button(
        "Generate PDF Report",
        type="primary",
        use_container_width=True,
    ):

        st.session_state.report_pdf = None
        st.session_state.report_fingerprint = None

        try:
            with st.status(
                "Preparing professional report...",
                expanded=True,
            ) as status:

                def progress(message):
                    st.write(message)

                progress("Collecting analysis measurements...")

                # Reuse only evidence stored with matching provenance.
                evidence_cache = st.session_state.setdefault(
                    "report_evidence_cache",
                    {},
                )

                existing = {
                    option: get_cached_evidence(
                        evidence_cache,
                        analysis_data,
                        option,
                    )
                    for option in selected
                }

                evidence = collect_selected_evidence(
                    analysis_data,
                    selected=selected,
                    existing=existing,
                    progress=progress,
                )

                for option, result in evidence.items():
                    if result is not None:
                        store_cached_evidence(
                            evidence_cache,
                            analysis_data,
                            option,
                            result,
                        )

                progress("Preparing interpretation...")

                interpretation = generate_report_interpretation(
                    analysis_data,
                    enabled=include_ai,
                    progress=progress,
                )

                progress("Rendering satellite imagery and charts...")

                pdf_bytes = generate_real_report(
                    analysis_data,
                    progress=progress,
                    evidence=evidence,
                    interpretation=interpretation,
                    preset=preset,
                )

                st.session_state.report_pdf = pdf_bytes
                st.session_state.report_fingerprint = fingerprint

                status.update(
                    label="Report ready",
                    state="complete",
                    expanded=False,
                )

        except Exception as error:
            st.error("Report generation failed.")
            with st.expander("Technical details"):
                st.exception(error)

    pdf_bytes = st.session_state.get("report_pdf")

    if pdf_bytes and st.session_state.get("report_fingerprint") == fingerprint:

        st.success("Your professional PDF report is ready.")

        filename = (
            "SetQuery_Report_"
            + analysis_data["before_date"]
            + "_"
            + analysis_data["after_date"]
            + ".pdf"
        )

        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True,
        )

        render_print_option(
            pdf_bytes,
            key="comparison_print",
        )
