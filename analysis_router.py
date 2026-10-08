from datetime import date, datetime

from analysis import (
    prepare_modern_analysis,
    analyze_prepared_area,
    get_prepared_satellite_images,
    get_prepared_change_map,
)
from burn_analysis import analyze_burn_evidence
from vegetation_stress_analysis import analyze_vegetation_stress
from flood_analysis import analyze_flood_evidence
from historical_analysis import (
    analyze_historical_area,
    get_historical_satellite_images,
)


# ==========================================================
# ANALYSIS MODE BOUNDARY
# ==========================================================

# Conservative application boundary for the current
# Sentinel-2 SR + Dynamic World workflow.
#
# Earlier requests use one common Landsat methodology
# for BOTH periods rather than mixing classification systems.
MODERN_MODE_START = date(
    2017,
    1,
    1,
)


# ==========================================================
# DATE HELPER
# ==========================================================

def _parse_date(value):
    """Normalize a date value."""

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    return datetime.strptime(
        str(value),
        "%Y-%m-%d",
    ).date()


# ==========================================================
# ROUTING
# ==========================================================

def choose_analysis_mode(
    before_date,
    after_date,
):
    """
    Select one internally consistent analysis methodology.

    If both target dates are within the modern analysis
    period, use Sentinel-2 + Dynamic World.

    If either period predates that boundary, use Landsat
    spectral analysis for BOTH periods.
    """

    before = _parse_date(
        before_date
    )

    after = _parse_date(
        after_date
    )

    if (
        before >= MODERN_MODE_START
        and after >= MODERN_MODE_START
    ):
        return "modern_ml"

    return "historical_spectral"


# ==========================================================
# ROUTED ANALYSIS
# ==========================================================

def run_routed_analysis(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=0.60,
    include_flood_evidence=False,
):
    """
    Run the appropriate SetQuery analysis methodology.

    Modern mode prepares its shared Earth Engine context
    once and reuses it for statistics, Sentinel-2 imagery,
    Change Map generation, burn evidence, and vegetation
    stress.

    Flood evidence (Sentinel-1 SAR) is opt-in via
    include_flood_evidence, since it builds its own
    separate Earth Engine collection and adds noticeable
    extra time regardless of analysis mode.
    """

    mode = choose_analysis_mode(
        before_date,
        after_date,
    )

    flood_evidence = None

    if include_flood_evidence:
        try:
            flood_evidence = analyze_flood_evidence(
                latitude=latitude,
                longitude=longitude,
                before_date=before_date,
                after_date=after_date,
                radius_km=radius_km,
            )
        except Exception:
            # Flood evidence is a supplementary, opt-in
            # indicator. If it fails for any reason, the
            # core analysis below must still be returned
            # successfully.
            flood_evidence = None

    # ------------------------------------------------------
    # MODERN
    # ------------------------------------------------------

    if mode == "modern_ml":

        context = (
            prepare_modern_analysis(
                latitude=latitude,
                longitude=longitude,
                before_date=before_date,
                after_date=after_date,
                radius_km=radius_km,
                confidence_threshold=(
                    confidence_threshold
                ),
            )
        )

        result = (
            analyze_prepared_area(
                context
            )
        )

        images = (
            get_prepared_satellite_images(
                context
            )
        )

        change_map = (
            get_prepared_change_map(
                context
            )
        )

        try:
            burn_evidence = analyze_burn_evidence(
                context
            )
        except Exception:
            # Burn evidence is a supplementary indicator.
            # If it fails for any reason, the core land-cover
            # analysis above must still be returned
            # successfully.
            burn_evidence = None

        try:
            vegetation_stress = analyze_vegetation_stress(
                context
            )
        except Exception:
            # Vegetation stress is a supplementary indicator.
            # If it fails for any reason, the core land-cover
            # analysis above must still be returned
            # successfully.
            vegetation_stress = None

        return {
            "mode":
                "modern_ml",

            "mode_label":
                "Modern ML",

            "method":
                "Sentinel-2 + Dynamic World ML",

            "approximate_resolution_m":
                10,

            "result":
                result,

            "images":
                images,

            "change_map":
                change_map,

            "burn_evidence":
                burn_evidence,

            "vegetation_stress":
                vegetation_stress,

            "flood_evidence":
                flood_evidence,
        }

    # ------------------------------------------------------
    # HISTORICAL
    # ------------------------------------------------------

    historical_result = (
        analyze_historical_area(
            latitude=latitude,
            longitude=longitude,
            before_date=before_date,
            after_date=after_date,
            radius_km=radius_km,
        )
    )

    historical_images = (
        get_historical_satellite_images(
            latitude=latitude,
            longitude=longitude,
            before_date=before_date,
            after_date=after_date,
            radius_km=radius_km,
        )
    )

    return {
        "mode":
            "historical_spectral",

        "mode_label":
            "Historical Spectral",

        "method":
            "Landsat spectral comparison",

        "approximate_resolution_m":
            30,

        "result":
            historical_result,

        "images":
            historical_images,

        # Historical mode deliberately does not fabricate
        # Dynamic World-style categorical transition maps.
        "change_map":
            None,

        # Burn evidence and vegetation stress are currently
        # only implemented for Modern mode.
        "burn_evidence":
            None,

        "vegetation_stress":
            None,

        # Flood evidence does not depend on the modern/
        # historical classification boundary, since it uses
        # Sentinel-1 SAR directly. It is still included here
        # if the user opted in.
        "flood_evidence":
            flood_evidence,
    }