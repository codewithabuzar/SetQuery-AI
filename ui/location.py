"""
Location search and geocoding for SetQuery.
"""

import streamlit as st
from geopy.geocoders import Nominatim

GEOCODER_USER_AGENT = "setquery-ai-student-project"
GEOCODER_RESULT_LIMIT = 5
GEOCODER_TIMEOUT_SECONDS = 10


@st.cache_data(ttl=3600, show_spinner=False)
def search_locations(query):
    """Search Nominatim for multiple candidate locations."""
    query = query.strip()
    if not query:
        return []

    geocoder = Nominatim(user_agent=GEOCODER_USER_AGENT)

    try:
        matches = geocoder.geocode(
            query,
            exactly_one=False,
            limit=GEOCODER_RESULT_LIMIT,
            addressdetails=True,
            timeout=GEOCODER_TIMEOUT_SECONDS,
        )
    except Exception as error:
        raise ValueError(
            "Location search is temporarily unavailable. "
            "Check your connection and try again."
        ) from error

    if not matches:
        return []

    results, seen = [], set()

    for match in matches:
        latitude = float(match.latitude)
        longitude = float(match.longitude)
        address = match.address or query
        key = (round(latitude, 6), round(longitude, 6), address)

        if key in seen:
            continue

        seen.add(key)
        results.append({"address": address, "latitude": latitude, "longitude": longitude})

    return results


def perform_location_search(query):
    """Resolve search text into candidate locations."""
    st.session_state.location_search_error = None
    st.session_state.location_matches = []
    st.session_state.selected_location = None
    st.session_state.selected_location_index = 0

    query = query.strip()
    if not query:
        st.session_state.location_search_error = "Enter a location to search."
        return

    try:
        matches = search_locations(query)
    except ValueError as error:
        st.session_state.location_search_error = str(error)
        return

    if not matches:
        st.session_state.location_search_error = (
            "No matching location was found. Try adding a city, state, or country."
        )
        return

    st.session_state.location_matches = matches
    st.session_state.selected_location = matches[0]

    st.session_state.clicked_latitude = None
    st.session_state.clicked_longitude = None
    st.session_state.location_source = "search"