"""On-demand high-resolution imagery for SetQuery PDF reports."""

import ee

from analysis.validation import validate_analysis_request
from analysis.ee_helpers import _create_area
from analysis.collections import _build_sentinel_collection

from .imagery import fetch_report_image


REPORT_IMAGE_DIMENSIONS = 1200


def get_modern_high_res_images(analysis_data):
    """
    Fetch high-resolution Sentinel-2 Before/After composites.

    This does not rerun Dynamic World classification or
    numerical analysis. It only builds Sentinel-2 imagery
    collections for the selected date windows.
    """

    request = validate_analysis_request(
        latitude=analysis_data["latitude"],
        longitude=analysis_data["longitude"],
        before_date=analysis_data["before_date"],
        after_date=analysis_data["after_date"],
        radius_km=analysis_data["radius_km"],
    )

    area = _create_area(
        request["latitude"],
        request["longitude"],
        request["radius_km"],
    )

    before_collection = _build_sentinel_collection(
        area,
        request["before_window"],
    )

    after_collection = _build_sentinel_collection(
        area,
        request["after_window"],
    )

    visualization = {
        "bands": ["B4", "B3", "B2"],
        "min": 0,
        "max": 3000,
        "gamma": 1.1,
    }

    params = {
        "region": area,
        "dimensions": REPORT_IMAGE_DIMENSIONS,
        "format": "png",
    }

    images = {}

    for name, collection in (
        ("before_url", before_collection),
        ("after_url", after_collection),
    ):
        image = (
            collection.median()
            .clip(area)
            .visualize(**visualization)
        )

        url = image.getThumbURL(params)

        images[name] = fetch_report_image(
            url,
            timeout=90,
        )

    return images
