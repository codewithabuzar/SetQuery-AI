from .config import *
from .errors import AnalysisDataError
from .validation import validate_analysis_request
from .ee_helpers import _create_area, _get_combined_counts
from .collections import (
    _build_dynamic_world_collection,
    _build_sentinel_collection,
)
from .consensus import _build_temporal_consensus

def prepare_modern_analysis(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """
    Build the shared Modern analysis context once.

    The routed application path reuses this context for:
    - numerical analysis;
    - Sentinel-2 previews;
    - Change Map generation.

    This avoids rebuilding and recounting the same
    Dynamic World and Sentinel-2 collections.

    Observation counts for all four collections are fetched
    using a single combined Earth Engine request instead of
    four separate requests.
    """

    request = validate_analysis_request(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=confidence_threshold,
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

    before_dw_collection = (
        _build_dynamic_world_collection(
            area,
            request[
                "before_window"
            ],
        )
    )

    after_dw_collection = (
        _build_dynamic_world_collection(
            area,
            request[
                "after_window"
            ],
        )
    )

    before_sentinel_collection = (
        _build_sentinel_collection(
            area,
            request[
                "before_window"
            ],
        )
    )

    after_sentinel_collection = (
        _build_sentinel_collection(
            area,
            request[
                "after_window"
            ],
        )
    )

    counts = _get_combined_counts(
        {
            "before_dw":
                before_dw_collection,

            "after_dw":
                after_dw_collection,

            "before_sentinel":
                before_sentinel_collection,

            "after_sentinel":
                after_sentinel_collection,
        }
    )

    before_dw_count = counts[
        "before_dw"
    ]

    after_dw_count = counts[
        "after_dw"
    ]

    before_sentinel_count = counts[
        "before_sentinel"
    ]

    after_sentinel_count = counts[
        "after_sentinel"
    ]

    if before_dw_count == 0:
        raise AnalysisDataError(
            "No Dynamic World observations were found "
            "for the BEFORE composite window."
        )

    if after_dw_count == 0:
        raise AnalysisDataError(
            "No Dynamic World observations were found "
            "for the AFTER composite window."
        )

    if before_sentinel_count == 0:
        raise AnalysisDataError(
            "No usable Sentinel-2 observations were found "
            "for the BEFORE composite window."
        )

    if after_sentinel_count == 0:
        raise AnalysisDataError(
            "No usable Sentinel-2 observations were found "
            "for the AFTER composite window."
        )

    before_consensus = (
        _build_temporal_consensus(
            before_dw_collection,
            request[
                "confidence_threshold"
            ],
        )
    )

    after_consensus = (
        _build_temporal_consensus(
            after_dw_collection,
            request[
                "confidence_threshold"
            ],
        )
    )

    comparable = (
        before_consensus[
            "valid"
        ]
        .And(
            after_consensus[
                "valid"
            ]
        )
    )

    before_land = (
        before_consensus[
            "land"
        ]
        .updateMask(
            comparable
        )
    )

    after_land = (
        after_consensus[
            "land"
        ]
        .updateMask(
            comparable
        )
    )

    before_vegetation = (
        before_land
        .gte(1)
        .And(
            before_land.lte(5)
        )
    )

    after_vegetation = (
        after_land
        .gte(1)
        .And(
            after_land.lte(5)
        )
    )

    before_water = (
        before_land.eq(0)
    )

    after_water = (
        after_land.eq(0)
    )

    before_built = (
        before_land.eq(6)
    )

    after_built = (
        after_land.eq(6)
    )

    before_bare = (
        before_land.eq(7)
    )

    after_bare = (
        after_land.eq(7)
    )

    vegetation_to_built = (
        before_vegetation
        .And(
            after_built
        )
    )

    built_to_vegetation = (
        before_built
        .And(
            after_vegetation
        )
    )

    bare_to_built = (
        before_bare
        .And(
            after_built
        )
    )

    water_to_nonwater = (
        before_water
        .And(
            after_land.neq(0)
        )
    )

    nonwater_to_water = (
        before_land
        .neq(0)
        .And(
            after_water
        )
    )

    return {
        "request":
            request,

        "area":
            area,

        "before_dw_collection":
            before_dw_collection,

        "after_dw_collection":
            after_dw_collection,

        "before_dw_count":
            before_dw_count,

        "after_dw_count":
            after_dw_count,

        "before_consensus":
            before_consensus,

        "after_consensus":
            after_consensus,

        "comparable":
            comparable,

        "before_land":
            before_land,

        "after_land":
            after_land,

        "before_vegetation":
            before_vegetation,

        "after_vegetation":
            after_vegetation,

        "before_water":
            before_water,

        "after_water":
            after_water,

        "before_built":
            before_built,

        "after_built":
            after_built,

        "before_bare":
            before_bare,

        "after_bare":
            after_bare,

        "vegetation_to_built":
            vegetation_to_built,

        "built_to_vegetation":
            built_to_vegetation,

        "bare_to_built":
            bare_to_built,

        "water_to_nonwater":
            water_to_nonwater,

        "nonwater_to_water":
            nonwater_to_water,

        "before_sentinel_collection":
            before_sentinel_collection,

        "after_sentinel_collection":
            after_sentinel_collection,

        "before_sentinel_count":
            before_sentinel_count,

        "after_sentinel_count":
            after_sentinel_count,
    }

