from .config import *
from .errors import AnalysisDataError
from .validation import validate_analysis_request
from .ee_helpers import _create_area, _get_collection_count
from .collections import _build_sentinel_collection
from .context import prepare_modern_analysis
from .statistics import analyze_prepared_area
from .imagery import (
    get_prepared_satellite_images,
    get_prepared_change_map,
)

def analyze_area(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """
    Run Modern analysis independently.

    The main routed application uses prepare_modern_analysis()
    once and calls analyze_prepared_area() instead.
    """

    context = prepare_modern_analysis(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=confidence_threshold,
    )

    return analyze_prepared_area(
        context
    )

def get_satellite_images(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
):
    """
    Generate Sentinel-2 previews independently.

    This standalone function intentionally does not build
    Dynamic World analysis state.
    """

    request = validate_analysis_request(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=(
            DEFAULT_CONFIDENCE_THRESHOLD
        ),
    )

    area = _create_area(
        request[
            "latitude"
        ],
        request[
            "longitude"
        ],
        request[
            "radius_km"
        ],
    )

    before_collection = (
        _build_sentinel_collection(
            area,
            request[
                "before_window"
            ],
        )
    )

    after_collection = (
        _build_sentinel_collection(
            area,
            request[
                "after_window"
            ],
        )
    )

    before_count = (
        _get_collection_count(
            before_collection,
            "Sentinel-2 BEFORE",
        )
    )

    after_count = (
        _get_collection_count(
            after_collection,
            "Sentinel-2 AFTER",
        )
    )

    if before_count == 0:
        raise AnalysisDataError(
            "No usable Sentinel-2 observations were found "
            "for the BEFORE composite window."
        )

    if after_count == 0:
        raise AnalysisDataError(
            "No usable Sentinel-2 observations were found "
            "for the AFTER composite window."
        )

    context = {
        "request":
            request,

        "area":
            area,

        "before_sentinel_collection":
            before_collection,

        "after_sentinel_collection":
            after_collection,

        "before_sentinel_count":
            before_count,

        "after_sentinel_count":
            after_count,
    }

    return get_prepared_satellite_images(
        context
    )

def get_change_map(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """
    Generate the change map independently.

    The routed application reuses a shared prepared context.
    """

    context = prepare_modern_analysis(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=confidence_threshold,
    )

    return get_prepared_change_map(
        context
    )

