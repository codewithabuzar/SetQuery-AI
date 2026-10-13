import ee

from .config import *

def _build_dynamic_world_collection(
    area,
    window,
):
    """Build Dynamic World collection for one period."""

    return (
        ee.ImageCollection(
            DYNAMIC_WORLD_COLLECTION
        )
        .filterBounds(
            area
        )
        .filterDate(
            window[
                "effective_start"
            ],
            window[
                "effective_end_exclusive"
            ],
        )
    )

def _mask_sentinel_clouds(
    image,
):
    """Mask selected Sentinel-2 SCL classes."""

    scl = image.select(
        "SCL"
    )

    mask = (
        scl.neq(3)
        .And(
            scl.neq(8)
        )
        .And(
            scl.neq(9)
        )
        .And(
            scl.neq(10)
        )
        .And(
            scl.neq(11)
        )
    )

    return image.updateMask(
        mask
    )

def _build_sentinel_collection(
    area,
    window,
):
    """Build cloud-masked Sentinel-2 SR collection."""

    return (
        ee.ImageCollection(
            SENTINEL_COLLECTION
        )
        .filterBounds(
            area
        )
        .filterDate(
            window[
                "effective_start"
            ],
            window[
                "effective_end_exclusive"
            ],
        )
        .filter(
            ee.Filter.lt(
                "CLOUDY_PIXEL_PERCENTAGE",
                90,
            )
        )
        .map(
            _mask_sentinel_clouds
        )
    )

