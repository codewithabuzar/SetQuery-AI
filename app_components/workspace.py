"""Empty workspace and reference map for SetQuery AI."""

import streamlit as st
from ui import build_location_from_click, build_study_area_map


def render_empty_workspace(radius_km):
    st.markdown('<div class="sq-workspace-spacer"></div>', unsafe_allow_html=True)
    st.title("Satellite change analysis")
    if st.session_state.clicked_latitude and st.session_state.clicked_longitude:
        center_lat = st.session_state.clicked_latitude
        center_lon = st.session_state.clicked_longitude
        selected_location = build_location_from_click(center_lat, center_lon)
        location_label = selected_location["address"]
    elif st.session_state.selected_location:
        center_lat = st.session_state.selected_location["latitude"]
        center_lon = st.session_state.selected_location["longitude"]
        location_label = st.session_state.selected_location["address"]
        selected_location = st.session_state.selected_location
    else:
        center_lat = 20.5937
        center_lon = 78.9629
        location_label = None
        selected_location = None
    if selected_location is None:
        st.write(
            "Search for a location in the sidebar, "
            "choose the correct match, and set the "
            "analysis period and radius."
        )
        st.caption("Or click anywhere on the map below to set the analysis center.")
        st.caption("Sentinel-2 · Dynamic World · Landsat")
    else:
        st.write(
            "The analysis center is selected. "
            "Set the dates and radius, then run the analysis."
        )
        st.caption(location_label)
    map_key = "study_area_map"
    map_data = build_study_area_map(
        latitude=center_lat,
        longitude=center_lon,
        radius_km=radius_km,
        location_label=location_label,
        allow_click_select=True,
        map_key=map_key,
    )
    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]

        st.session_state.clicked_latitude = clicked_lat
        st.session_state.clicked_longitude = clicked_lon
        st.session_state.location_source = "click"
        st.session_state.selected_location = None
        st.session_state.location_matches = []
        st.session_state.reset_location_index = True
        st.session_state.location_search_error = None

        st.info(
            f" Location set: {clicked_lat:.5f}, {clicked_lon:.5f} — "
            "Click Analyze in the sidebar to run the analysis."
        )
        st.rerun()
    st.caption(
        "Geographic context only · the outlined circle "
        "is the current study area. Satellite analysis "
        "uses Sentinel-2 or Landsat through Earth Engine."
    )
    st.caption("Sentinel-2 · Dynamic World · Landsat")
    st.stop()
