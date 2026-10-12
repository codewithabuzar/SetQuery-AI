"""
Session state management for SetQuery.
"""

import streamlit as st 

SESSION_DEFAULTS = {
    "app_view": "home",
    "analysis_data": None,
    "trend_data": None,
    "flood_evidence_data": None,
    "flood_evidence_error": None,
    "burn_evidence_data": None,
    "burn_evidence_error": None,
    "vegetation_stress_data": None,
    "vegetation_stress_error": None,
    "ai_answer": None,
    "ai_source": None,
    "ai_status": None,
    "location_matches": [],
    "selected_location": None,
    "selected_location_index": 0,
    "location_search_error": None,
    "clicked_latitude": None,
    "clicked_longitude": None,
    "location_source": None,
}


def initialize_session_state():
    """Initialize all session state variables with defaults."""
    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value