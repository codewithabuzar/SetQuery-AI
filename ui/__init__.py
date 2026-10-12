"""
SetQuery UI Module
Organized UI components for the Streamlit application.
"""

from .helpers import (
    section,
    sensor_text,
    coverage_status_class,
    render_status,
    render_legend,
    metric_grid,
    render_before_after_compare,
    open_workspace,
    open_home,
    clear_analysis,
    build_location_from_click,
)

from .location import (
    search_locations,
    perform_location_search,
)

from .map import (
    build_study_area_map,
)

from .charts import (
    grouped_bar_chart,
    modern_land_cover_chart,
    historical_index_chart,
    trend_composition_chart,
)

from .fragments import (
    render_burn_evidence_tab,
    render_vegetation_stress_tab,
    render_flood_evidence_tab,
    render_ai_qa_section,
    resolve_ai_answer,
)

from .state import (
    SESSION_DEFAULTS,
    initialize_session_state,
)

__all__ = [
    "section",
    "sensor_text",
    "render_status",
    "render_legend",
    "metric_grid",
    "render_before_after_compare",
    "open_workspace",
    "open_home",
    "clear_analysis",
    "search_locations",
    "perform_location_search",
    "build_study_area_map",
    "grouped_bar_chart",
    "modern_land_cover_chart",
    "historical_index_chart",
    "trend_composition_chart",
    "render_burn_evidence_tab",
    "render_vegetation_stress_tab",
    "render_flood_evidence_tab",
    "render_ai_qa_section",
    "SESSION_DEFAULTS",
    "initialize_session_state",
]