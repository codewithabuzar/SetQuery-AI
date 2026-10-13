import ee

from .config import *
from .errors import AnalysisDataError
from .ee_helpers import _observation_warnings

def analyze_prepared_area(
    context,
):
    """Calculate statistics from a prepared Modern context."""

    request = context[
        "request"
    ]

    area = context[
        "area"
    ]

    km2 = (
        ee.Image.pixelArea()
        .divide(1e6)
    )

    stats_image = ee.Image.cat(
        [
            km2
            .updateMask(
                context[
                    "comparable"
                ]
            )
            .rename(
                "comparable"
            ),

            km2
            .updateMask(
                context[
                    "before_vegetation"
                ]
            )
            .rename(
                "before_vegetation"
            ),

            km2
            .updateMask(
                context[
                    "after_vegetation"
                ]
            )
            .rename(
                "after_vegetation"
            ),

            km2
            .updateMask(
                context[
                    "before_water"
                ]
            )
            .rename(
                "before_water"
            ),

            km2
            .updateMask(
                context[
                    "after_water"
                ]
            )
            .rename(
                "after_water"
            ),

            km2
            .updateMask(
                context[
                    "before_built"
                ]
            )
            .rename(
                "before_built"
            ),

            km2
            .updateMask(
                context[
                    "after_built"
                ]
            )
            .rename(
                "after_built"
            ),

            km2
            .updateMask(
                context[
                    "before_bare"
                ]
            )
            .rename(
                "before_bare"
            ),

            km2
            .updateMask(
                context[
                    "after_bare"
                ]
            )
            .rename(
                "after_bare"
            ),

            km2
            .updateMask(
                context[
                    "vegetation_to_built"
                ]
            )
            .rename(
                "vegetation_to_built"
            ),

            km2
            .updateMask(
                context[
                    "built_to_vegetation"
                ]
            )
            .rename(
                "built_to_vegetation"
            ),

            km2
            .updateMask(
                context[
                    "bare_to_built"
                ]
            )
            .rename(
                "bare_to_built"
            ),

            km2
            .updateMask(
                context[
                    "water_to_nonwater"
                ]
            )
            .rename(
                "water_to_nonwater"
            ),

            km2
            .updateMask(
                context[
                    "nonwater_to_water"
                ]
            )
            .rename(
                "nonwater_to_water"
            ),
        ]
    )

    radius_km_value = float(
        request.get(
            "radius_km",
            10,
        )
    )

    analysis_scale_m = max(
        10,
        min(
            40,
            (
                3.1416
                * (radius_km_value * 1000) ** 2
                / 150000
            ) ** 0.5,
        ),
    )

    try:
        combined = ee.Dictionary(
            {
                "stats":
                    stats_image.reduceRegion(
                        reducer=(
                            ee.Reducer.sum()
                        ),
                        geometry=area,
                        scale=analysis_scale_m,
                        maxPixels=1e9,
                        tileScale=4,
                    ),

                "total_area_km2":
                    area
                    .area()
                    .divide(1e6),
            }
        ).getInfo()

        stats = combined[
            "stats"
        ]

        total_area_km2 = float(
            combined[
                "total_area_km2"
            ]
        )

    except Exception as error:

        raise AnalysisDataError(
            "Earth Engine could not calculate "
            "land-cover statistics."
        ) from error

    def stat_value(
        name,
    ):
        value = stats.get(
            name
        )

        if value is None:
            return 0.0

        return float(
            value
        )

    comparable_area_km2 = (
        stat_value(
            "comparable"
        )
    )

    if total_area_km2 > 0:
        coverage_percent = (
            comparable_area_km2
            / total_area_km2
            * 100
        )

    else:
        coverage_percent = 0.0

    warnings = list(
        request[
            "warnings"
        ]
    )

    warnings.extend(
        _observation_warnings(
            context[
                "before_dw_count"
            ],
            context[
                "after_dw_count"
            ],
            "Dynamic World",
        )
    )

    if coverage_percent < 20:
        warnings.append(
            "Comparable coverage is very low and is "
            "insufficient for broad area-level conclusions."
        )

    elif coverage_percent < 40:
        warnings.append(
            "Comparable coverage is limited. Area-wide "
            "conclusions should be made cautiously."
        )

    return {
        "before_observations":
            context[
                "before_dw_count"
            ],

        "after_observations":
            context[
                "after_dw_count"
            ],

        "total_area_km2":
            total_area_km2,

        "comparable_area_km2":
            comparable_area_km2,

        "coverage_percent":
            coverage_percent,

        "before_vegetation_km2":
            stat_value(
                "before_vegetation"
            ),

        "after_vegetation_km2":
            stat_value(
                "after_vegetation"
            ),

        "before_built_km2":
            stat_value(
                "before_built"
            ),

        "after_built_km2":
            stat_value(
                "after_built"
            ),

        "before_water_km2":
            stat_value(
                "before_water"
            ),

        "after_water_km2":
            stat_value(
                "after_water"
            ),

        "before_bare_km2":
            stat_value(
                "before_bare"
            ),

        "after_bare_km2":
            stat_value(
                "after_bare"
            ),

        "vegetation_to_built_km2":
            stat_value(
                "vegetation_to_built"
            ),

        "built_to_vegetation_km2":
            stat_value(
                "built_to_vegetation"
            ),

        "bare_to_built_km2":
            stat_value(
                "bare_to_built"
            ),

        "water_to_nonwater_km2":
            stat_value(
                "water_to_nonwater"
            ),

        "nonwater_to_water_km2":
            stat_value(
                "nonwater_to_water"
            ),

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

        "date_separation_days":
            request[
                "date_separation_days"
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

