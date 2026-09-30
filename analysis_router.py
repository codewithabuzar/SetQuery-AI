from datetime import date, datetime

from analysis import (
    analyze_area,
    get_satellite_images,
    get_change_map,
)
from historical_analysis import (
    analyze_historical_area,
    get_historical_satellite_images,
)


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


def _parse_date(value):
    """
    Normalize a date value.
    """

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    return datetime.strptime(
        str(value),
        "%Y-%m-%d",
    ).date()


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


def run_routed_analysis(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=0.60,
):
    """
    Run the appropriate SetQuery analysis methodology.
    """

    mode = choose_analysis_mode(
        before_date,
        after_date,
    )

    if mode == "modern_ml":

        result = analyze_area(
            latitude=latitude,
            longitude=longitude,
            before_date=before_date,
            after_date=after_date,
            radius_km=radius_km,
            confidence_threshold=confidence_threshold,
        )

        images = get_satellite_images(
            latitude=latitude,
            longitude=longitude,
            before_date=before_date,
            after_date=after_date,
            radius_km=radius_km,
        )

        change_map = get_change_map(
            latitude=latitude,
            longitude=longitude,
            before_date=before_date,
            after_date=after_date,
            radius_km=radius_km,
            confidence_threshold=confidence_threshold,
        )

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
        }

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
    }