import ee

from .config import *
from .errors import AnalysisDataError

def _create_area(
    latitude,
    longitude,
    radius_km,
):
    """Create study geometry."""

    point = ee.Geometry.Point(
        [
            longitude,
            latitude,
        ]
    )

    return point.buffer(
        radius_km * 1000
    )

def _get_collection_count(
    collection,
    label,
):
    """Retrieve a single Earth Engine collection count."""

    try:
        return int(
            collection
            .size()
            .getInfo()
        )

    except Exception as error:

        raise AnalysisDataError(
            f"Could not check {label} observations. "
            "Earth Engine or the network may be "
            "temporarily unavailable."
        ) from error

def _get_combined_counts(
    collections,
):
    """
    Retrieve multiple Earth Engine collection counts using a
    single combined request.

    This replaces several separate .size().getInfo() calls
    with one network round trip. The counted values and
    methodology are unchanged.

    collections: dict of {label: ee.ImageCollection}
    returns: dict of {label: int}
    """

    try:
        sizes = ee.Dictionary(
            {
                name: collection.size()
                for name, collection in collections.items()
            }
        )

        info = sizes.getInfo()

    except Exception as error:

        raise AnalysisDataError(
            "Could not check Earth Engine observation "
            "counts. Earth Engine or the network may be "
            "temporarily unavailable."
        ) from error

    return {
        key: int(value)
        for key, value in info.items()
    }

def _observation_warnings(
    before_count,
    after_count,
    dataset_name,
):
    """Generate warnings for unusually small collections."""

    warnings = []

    if (
        before_count
        < LOW_OBSERVATION_WARNING_COUNT
    ):
        warnings.append(
            f"Only {before_count} {dataset_name} "
            "observation(s) were available for the "
            "BEFORE period."
        )

    if (
        after_count
        < LOW_OBSERVATION_WARNING_COUNT
    ):
        warnings.append(
            f"Only {after_count} {dataset_name} "
            "observation(s) were available for the "
            "AFTER period."
        )

    return warnings

