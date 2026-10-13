"""Analysis execution for SetQuery AI."""

import time
import streamlit as st
from ui import clear_analysis, build_location_from_click
from analysis import AnalysisValidationError, AnalysisDataError
from historical_analysis import HistoricalValidationError, HistoricalDataError
from analysis_router import run_routed_analysis
from trend_analysis import analyze_trend

def run_selected_analysis(run_clicked, analysis_type, before_date, after_date, trend_dates, radius_km, confidence_threshold):
    if run_clicked:

        clear_analysis()

        if st.session_state.location_source == "click" and st.session_state.clicked_latitude:
            selected_location = build_location_from_click(
                st.session_state.clicked_latitude, st.session_state.clicked_longitude
            )
        elif st.session_state.selected_location:
            selected_location = st.session_state.selected_location
        else:
            selected_location = None

        if selected_location is None:
            st.error("Select a location via search or click on the map before analyzing.")

        elif analysis_type == "Compare two dates":

            try:
                with st.spinner("Analyzing satellite data..."):
                    start_time = time.perf_counter()
                    routed = run_routed_analysis(
                        latitude=selected_location["latitude"],
                        longitude=selected_location["longitude"],
                        before_date=str(before_date),
                        after_date=str(after_date),
                        radius_km=radius_km,
                        confidence_threshold=confidence_threshold,
                    )

                elapsed = time.perf_counter() - start_time
                print(f"SetQuery Earth Engine analysis: {elapsed:.1f} seconds")

                st.session_state.analysis_data = {
                    "location": selected_location["address"],
                    "latitude": selected_location["latitude"],
                    "longitude": selected_location["longitude"],
                    "radius_km": radius_km,
                    "before_date": str(before_date),
                    "after_date": str(after_date),
                    **routed,
                }

            except (
                AnalysisValidationError,
                HistoricalValidationError,
                AnalysisDataError,
                HistoricalDataError,
                ValueError,
            ) as error:
                st.error(str(error))

            except Exception as error:
                st.error("Analysis could not be completed.")
                with st.expander("Technical details"):
                    st.exception(error)

        else:

            try:
                with st.spinner("Analyzing satellite data..."):
                    start_time = time.perf_counter()
                    trend_result = analyze_trend(
                        latitude=selected_location["latitude"],
                        longitude=selected_location["longitude"],
                        dates=[str(single_date) for single_date in trend_dates],
                        radius_km=radius_km,
                        confidence_threshold=confidence_threshold,
                    )

                elapsed = time.perf_counter() - start_time
                print(f"SetQuery Earth Engine trend analysis: {elapsed:.1f} seconds")

                st.session_state.trend_data = {
                    "location": selected_location["address"],
                    "latitude": selected_location["latitude"],
                    "longitude": selected_location["longitude"],
                    "radius_km": radius_km,
                    **trend_result,
                }

            except (
                AnalysisValidationError,
                AnalysisDataError,
                ValueError,
            ) as error:
                st.error(str(error))

            except Exception as error:
                st.error("Trend analysis could not be completed.")
                with st.expander("Technical details"):
                    st.exception(error)
