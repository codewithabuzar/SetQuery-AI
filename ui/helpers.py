"""
UI helper functions for SetQuery.
"""

import streamlit as st


def section(label, title, description=None):
    """Render a minimal section heading."""
    if label:
        st.markdown(f'<div class="sq-section-label">{label}</div>', unsafe_allow_html=True)
    st.subheader(title)
    if description:
        st.caption(description)


def sensor_text(sensor_list):
    """Format Landsat sensor metadata."""
    if not sensor_list:
        return "No sensor metadata"
    return ", ".join(f"{item['name']} ({item['observations']} obs.)" for item in sensor_list)


def coverage_status_class(level):
    """Select status style from coverage category."""
    if level == "GOOD":
        return "sq-status-good"
    if level in ("MODERATE", "LIMITED"):
        return "sq-status-warning"
    return "sq-status-danger"


def render_status(text, level):
    """Render restrained analysis-quality status."""
    css_class = coverage_status_class(level)
    st.markdown(f'<div class="sq-status {css_class}">{text}</div>', unsafe_allow_html=True)


def render_legend(items):
    """Render a row of colored legend dots with labels."""
    spans = "".join(
        f'<span class="sq-legend-item">'
        f'<span class="sq-dot" style="background:{color}"></span>{label}</span>'
        for color, label in items
    )
    st.markdown(f'<div class="sq-legend">{spans}</div>', unsafe_allow_html=True)


def metric_grid(items, per_row=2):
    """Render metrics in evenly spaced rows."""
    for start in range(0, len(items), per_row):
        row_items = items[start:start + per_row]
        for col, item in zip(st.columns(len(row_items)), row_items):
            col.metric(*item)


def render_before_after_compare(tabs, before_url, after_url, before_caption, after_caption, before, after):
    """Render the shared Before / After / Compare tab pattern."""
    before_tab, after_tab, compare_tab = tabs

    with before_tab:
        st.image(before_url, width="stretch")
        st.caption(before_caption)

    with after_tab:
        st.image(after_url, width="stretch")
        st.caption(after_caption)

    with compare_tab:
        col_before, col_after = st.columns(2)
        with col_before:
            st.markdown(f"### Before · {before}")
            st.image(before_url, width="stretch")
        with col_after:
            st.markdown(f"### After · {after}")
            st.image(after_url, width="stretch")


def open_workspace():
    """Open the analysis workspace."""
    st.session_state.app_view = "workspace"


def open_home():
    """Return to the landing page."""
    st.session_state.app_view = "home"


def clear_analysis():
    """Clear current analysis and query state."""
    st.session_state.analysis_data = None
    st.session_state.trend_data = None
    st.session_state.flood_evidence_data = None
    st.session_state.flood_evidence_error = None
    st.session_state.burn_evidence_data = None
    st.session_state.burn_evidence_error = None
    st.session_state.vegetation_stress_data = None
    st.session_state.vegetation_stress_error = None
    st.session_state.ai_answer = None
    st.session_state.ai_source = None
    st.session_state.ai_status = None


def build_location_from_click(latitude, longitude):
    """Build a location dict for a point selected by clicking the map."""
    return {
        "address": f"Custom location ({latitude:.5f}, {longitude:.5f})",
        "latitude": latitude,
        "longitude": longitude,
    }

def _paired_values(data, label_key="label", value_key="value"):
    """
    Extract paired labels and values from land cover or similar data.

    Args:
        data: List of dicts with label/value keys, or dict of label->value
        label_key: Key name for labels (default: 'label')
        value_key: Key name for values (default: 'value')

    Returns:
        tuple: (labels, values) as two separate lists
    """
    if not data:
        return [], []

    if isinstance(data, dict):
        labels = list(data.keys())
        values = list(data.values())
    elif isinstance(data, list):
        labels = [item.get(label_key, str(i)) for i, item in enumerate(data)]
        values = [item.get(value_key, 0) for item in data]
    else:
        return [], []

    return labels, values