"""
Verified application knowledge for SetQuery AI.

This describes capabilities and limitations.
It does not represent measured satellite results.
"""

APP_KNOWLEDGE = {
    "name": "SetQuery AI",
    "purpose": (
        "Satellite-based change detection and grounded "
        "geospatial analysis."
    ),
    "location_selection": (
        "Users can search for a named place or click the "
        "interactive map to choose an analysis center."
    ),
    "study_area": (
        "Analysis uses a circular study area with a radius "
        "between 1 and 20 km."
    ),
    "modern_analysis": (
        "Modern mode uses Sentinel-2 imagery and Google "
        "Dynamic World land-cover probabilities for dates "
        "from 2017 onward. It compares water, vegetation, "
        "built-up land and bare ground."
    ),
    "historical_analysis": (
        "Historical mode uses Landsat spectral indices "
        "including NDVI, MNDWI and NDBI. These indicators "
        "are not direct categorical land-cover measurements."
    ),
    "automatic_routing": (
        "The application selects Modern ML when both dates "
        "are from 2017 onward. Otherwise it uses Historical "
        "Spectral analysis for both periods."
    ),
    "temporal_consensus": (
        "Modern analysis uses approximately 45-day windows "
        "around target dates and confidence-based temporal "
        "consensus. Comparable coverage is not accuracy."
    ),
    "change_detection": (
        "Modern analysis tracks vegetation-to-built, "
        "built-to-vegetation, bare-to-built, water-to-nonwater "
        "and nonwater-to-water transitions."
    ),
    "trend_analysis": (
        "Trend mode compares independently analyzed "
        "land-cover measurements across multiple dates "
        "using Sentinel-2 and Dynamic World."
    ),
    "burn_evidence": (
        "Burn Evidence uses Sentinel-2 NBR and dNBR. "
        "Severity categories are indicative and do not "
        "prove a fire occurred."
    ),
    "vegetation_stress": (
        "Vegetation Stress uses Sentinel-2 NDVI change "
        "to describe greenness variation. It does not "
        "confirm drought or crop damage."
    ),
    "flood_evidence": (
        "Flood Evidence uses Sentinel-1 SAR backscatter "
        "changes to identify possible surface-water change. "
        "It is not validated flood damage assessment."
    ),
    "interactive_map": (
        "The map supports location selection, study-area "
        "visualization and interactive Earth Engine layers "
        "for Modern ML results."
    ),
    "ai_assistant": (
        "Ask SetQuery AI explains application functionality "
        "and interprets available analysis measurements. "
        "It must not invent observations or causes."
    ),
    "limitations": (
        "Results are satellite-derived estimates. "
        "The application does not establish exact causes, "
        "individual-property changes or surveyed ground truth."
    ),
}


def get_app_knowledge():
    """Return a copy of the verified application knowledge."""
    return dict(APP_KNOWLEDGE)


APP_KNOWLEDGE.update({'creator': 'Mohd Abuzar', 'developer': 'Mohd Abuzar', 'project_identity': 'SetQuery AI is an open-source satellite change detection and grounded geospatial analysis application developed by Mohd Abuzar.', 'github_profile': 'https://github.com/codewithabuzar', 'github_repository': 'https://github.com/codewithabuzar/SetQuery-AI', 'license': 'MIT License', 'technology_stack': 'Python, Streamlit, Google Earth Engine, GeoPy, Google Dynamic World, Sentinel-2, Landsat, Sentinel-1 SAR, Folium, Altair and Google Gemini.', 'usage_guide': 'Open analysis, search for a location or select coordinates on the map, choose comparison dates or trend mode, select a radius between 1 and 20 km, click Analyze, review results, and ask questions.', 'modern_vs_historical': 'Modern ML uses Sentinel-2 and Dynamic World for dates from 2017 onward. Historical Spectral mode uses Landsat and spectral indices when either comparison date is before 2017.', 'burn_usage': 'Run Modern ML analysis, open Burn Evidence, and click Check burn evidence. NBR/dNBR provides indicative spectral evidence, not confirmed fire.', 'vegetation_usage': 'Run Modern ML analysis, open Vegetation Stress, and click Check vegetation stress. NDVI describes greenness changes, not confirmed drought.', 'flood_usage': 'Run Modern ML analysis, open Flood Evidence, and click Check flood evidence. Sentinel-1 SAR provides possible surface-water change evidence, not confirmed flood damage.', 'troubleshooting': 'Low coverage can result from insufficient usable observations or confidence filtering. Processing time depends on Earth Engine, datasets, radius and network conditions. Gemini can become unavailable because of API configuration, quota or service problems.', 'language_support': "Explain application features in English, Hindi or Hinglish according to the user's language. Do not invent measurements or personal details.", 'scientific_limits': 'Coverage is not classification accuracy. Satellite-derived estimates do not establish exact causes, individual-property changes, confirmed fires, confirmed drought or validated flood damage.', 'personal_information_policy': 'The verified developer name is Mohd Abuzar. Do not invent education, employment, age, address, biography or personal achievements.'})
