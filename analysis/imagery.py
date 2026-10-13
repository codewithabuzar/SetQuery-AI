import ee

from .config import *
from .errors import AnalysisDataError
from .ee_helpers import _observation_warnings

def get_prepared_satellite_images(
    context,
):
    """Generate true-color previews from shared context."""

    request = context[
        "request"
    ]

    area = context[
        "area"
    ]

    before_image = (
        context[
            "before_sentinel_collection"
        ]
        .median()
        .clip(
            area
        )
    )

    after_image = (
        context[
            "after_sentinel_collection"
        ]
        .median()
        .clip(
            area
        )
    )

    rgb_vis = {
        "bands": [
            "B4",
            "B3",
            "B2",
        ],
        "min":
            0,
        "max":
            3000,
        "gamma":
            1.1,
    }

    thumbnail_params = {
        "region":
            area,

        "dimensions":
            500,

        "format":
            "png",
    }

    try:
        before_url = (
            before_image
            .visualize(
                **rgb_vis
            )
            .getThumbURL(
                thumbnail_params
            )
        )

        after_url = (
            after_image
            .visualize(
                **rgb_vis
            )
            .getThumbURL(
                thumbnail_params
            )
        )

    except Exception as error:

        raise AnalysisDataError(
            "Earth Engine could not generate "
            "Sentinel-2 preview images."
        ) from error

    warnings = list(
        request[
            "warnings"
        ]
    )

    warnings.extend(
        _observation_warnings(
            context[
                "before_sentinel_count"
            ],
            context[
                "after_sentinel_count"
            ],
            "Sentinel-2",
        )
    )

    return {
        "before_url":
            before_url,

        "after_url":
            after_url,

        "before_sentinel_observations":
            context[
                "before_sentinel_count"
            ],

        "after_sentinel_observations":
            context[
                "after_sentinel_count"
            ],

        "before_window":
            request[
                "before_window"
            ],

        "after_window":
            request[
                "after_window"
            ],

        "warnings":
            warnings,
    }

def get_prepared_tile_layers(
    context,
):
    """
    Generate Earth Engine tile layer URLs for interactive Folium map.

    Returns tile URLs and visualization parameters for:
    - Before (Sentinel-2 true color)
    - After (Sentinel-2 true color)
    - Change map (transitions overlay)

    These tiles can be added as folium.TileLayer objects with
    getMapId() output. Users can toggle layers and zoom/pan.
    """

    request = context[
        "request"
    ]

    area = context[
        "area"
    ]

    # Before Sentinel-2 true color
    before_image = (
        context[
            "before_sentinel_collection"
        ]
        .median()
        .clip(
            area
        )
    )

    before_vis = {
        "min": 0,
        "max": 3000,
        "bands": ["B4", "B3", "B2"],
        "gamma": 1.1,
    }

    # After Sentinel-2 true color
    after_image = (
        context[
            "after_sentinel_collection"
        ]
        .median()
        .clip(
            area
        )
    )

    after_vis = {
        "min": 0,
        "max": 3000,
        "bands": ["B4", "B3", "B2"],
        "gamma": 1.1,
    }

    # Change map
    change = (
        ee.Image(0)
        .where(
            context[
                "vegetation_to_built"
            ],
            1,
        )
        .where(
            context[
                "built_to_vegetation"
            ],
            2,
        )
        .where(
            context[
                "bare_to_built"
            ],
            3,
        )
        .where(
            context[
                "nonwater_to_water"
            ],
            4,
        )
        .where(
            context[
                "water_to_nonwater"
            ],
            5,
        )
        .clip(
            area
        )
    )

    change_vis = {
        "min": 1,
        "max": 5,
        "palette": [
            "FF0000",
            "00FF00",
            "FFFF00",
            "0066FF",
            "FF8800",
        ],
    }

    try:
        before_map_id = before_image.visualize(**before_vis).getMapId()
        after_map_id = after_image.visualize(**after_vis).getMapId()

        # Change map with semi-transparent overlay on after image
        after_bg = after_image.visualize(
            min=0,
            max=3500,
            bands=["B4", "B3", "B2"],
            gamma=1.2,
        ).multiply(0.45).toUint8()

        change_colored = change.visualize(**change_vis)
        change_overlay = after_bg.blend(change_colored).clip(area)
        change_map_id = change_overlay.getMapId()

    except Exception as error:

        raise AnalysisDataError(
            "Earth Engine could not generate interactive tile layers."
        ) from error

    return {
        "before_tile_url": before_map_id["tile_fetcher"].url_format,
        "after_tile_url": after_map_id["tile_fetcher"].url_format,
        "change_tile_url": change_map_id["tile_fetcher"].url_format,
        "before_vis": before_vis,
        "after_vis": after_vis,
        "change_vis": change_vis,
    }

def get_prepared_change_map(
    context,
):
    """
    Generate the transition map thumbnail from shared context.

    focal_max is used only for display. Numerical statistics
    continue to use the original transition pixels.
    """

    request = context[
        "request"
    ]

    area = context[
        "area"
    ]

    change = (
        ee.Image(0)
        .where(
            context[
                "vegetation_to_built"
            ],
            1,
        )
        .where(
            context[
                "built_to_vegetation"
            ],
            2,
        )
        .where(
            context[
                "bare_to_built"
            ],
            3,
        )
        .where(
            context[
                "nonwater_to_water"
            ],
            4,
        )
        .where(
            context[
                "water_to_nonwater"
            ],
            5,
        )
        .clip(
            area
        )
    )

    display_radius = 2

    veg_to_built_display = (
        change.eq(1)
        .focal_max(
            radius=display_radius,
            units="pixels",
        )
    )

    built_to_veg_display = (
        change.eq(2)
        .focal_max(
            radius=display_radius,
            units="pixels",
        )
    )

    bare_to_built_display = (
        change.eq(3)
        .focal_max(
            radius=display_radius,
            units="pixels",
        )
    )

    new_water_display = (
        change.eq(4)
        .focal_max(
            radius=display_radius,
            units="pixels",
        )
    )

    lost_water_display = (
        change.eq(5)
        .focal_max(
            radius=display_radius,
            units="pixels",
        )
    )

    display_change = (
        ee.Image(0)
        .where(
            veg_to_built_display,
            1,
        )
        .where(
            built_to_veg_display,
            2,
        )
        .where(
            bare_to_built_display,
            3,
        )
        .where(
            new_water_display,
            4,
        )
        .where(
            lost_water_display,
            5,
        )
    )

    display_change = (
        display_change
        .updateMask(
            display_change.gt(0)
        )
        .clip(
            area
        )
    )

    background = (
        context[
            "after_sentinel_collection"
        ]
        .median()
        .clip(
            area
        )
        .visualize(
            bands=[
                "B4",
                "B3",
                "B2",
            ],
            min=0,
            max=3500,
            gamma=1.2,
        )
        .multiply(
            0.45
        )
        .toUint8()
    )

    colored_changes = (
        display_change
        .visualize(
            min=1,
            max=5,
            palette=[
                "FF0000",
                "00FF00",
                "FFFF00",
                "0066FF",
                "FF8800",
            ],
        )
    )

    final_map = (
        background
        .blend(
            colored_changes
        )
        .clip(
            area
        )
    )

    thumbnail_params = {
        "region":
            area,

        "dimensions":
            500,

        "format":
            "png",
    }

    try:
        change_url = (
            final_map
            .getThumbURL(
                thumbnail_params
            )
        )

    except Exception as error:

        raise AnalysisDataError(
            "Earth Engine could not generate "
            "the change-map preview."
        ) from error

    return {
        "change_url":
            change_url,

        "before_change_observations":
            context[
                "before_dw_count"
            ],

        "after_change_observations":
            context[
                "after_dw_count"
            ],

        "background_sentinel_observations":
            context[
                "after_sentinel_count"
            ],

        "classification_method":
            "dynamic_world_temporal_consensus",

        "confidence_threshold":
            request[
                "confidence_threshold"
            ],

        "min_confident_observations":
            MIN_CONFIDENT_OBSERVATIONS,

        "min_confidence_frequency":
            MIN_CONFIDENCE_FREQUENCY,

        "min_temporal_consensus":
            MIN_TEMPORAL_CONSENSUS,

        "before_window":
            request[
                "before_window"
            ],

        "after_window":
            request[
                "after_window"
            ],
    }

