from datetime import date, datetime

import ee

from analysis import (
    AnalysisValidationError,
    AnalysisDataError,
    DEFAULT_CONFIDENCE_THRESHOLD,
    MIN_CONFIDENT_OBSERVATIONS,
    MIN_CONFIDENCE_FREQUENCY,
    MIN_TEMPORAL_CONSENSUS,
    MIN_DATE_SEPARATION_DAYS,
    LOW_OBSERVATION_WARNING_COUNT,
    _parse_date,
    _validate_coordinates,
    _validate_radius,
    _validate_confidence_threshold,
    _create_area,
    _build_dynamic_world_collection,
    _build_window_metadata,
    _build_temporal_consensus,
    _get_combined_counts,
)

from analysis_router import MODERN_MODE_START


# ==========================================================
# CONFIGURATION
# ==========================================================

MIN_TREND_POINTS = 2
MAX_TREND_POINTS = 8

# A period is marked "reliable" if its own coverage percent
# meets this threshold. This mirrors the existing pairwise
# coverage-interpretation thresholds (section 17 of the
# project methodology), applied per-period here since trend
# analysis treats each date independently.
RELIABLE_COVERAGE_THRESHOLD = 20.0


# ==========================================================
# VALIDATION
# ==========================================================

def validate_trend_request(
    latitude,
    longitude,
    dates,
    radius_km,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """
    Validate a Multi-Period Trend request.

    Trend analysis reuses the Modern Dynamic World temporal
    consensus methodology independently for each date. It
    does not mix in Landsat historical spectral analysis,
    so every date must fall on or after MODERN_MODE_START.
    """

    (
        latitude,
        longitude,
    ) = _validate_coordinates(
        latitude,
        longitude,
    )

    radius_km = _validate_radius(
        radius_km
    )

    confidence_threshold = (
        _validate_confidence_threshold(
            confidence_threshold
        )
    )

    if (
        dates is None
        or len(dates) < MIN_TREND_POINTS
    ):
        raise AnalysisValidationError(
            "Trend analysis requires at least "
            f"{MIN_TREND_POINTS} dates."
        )

    if len(dates) > MAX_TREND_POINTS:
        raise AnalysisValidationError(
            "Trend analysis supports at most "
            f"{MAX_TREND_POINTS} dates."
        )

    parsed_dates = [
        _parse_date(
            value,
            "Trend date",
        )
        for value in dates
    ]

    sorted_dates = sorted(
        parsed_dates
    )

    if len(set(sorted_dates)) != len(sorted_dates):
        raise AnalysisValidationError(
            "Trend dates must be unique."
        )

    today = date.today()

    for single_date in sorted_dates:

        if single_date > today:
            raise AnalysisValidationError(
                "Trend dates cannot be in the future."
            )

        if single_date < MODERN_MODE_START:
            raise AnalysisValidationError(
                "Trend analysis currently uses the modern "
                "Dynamic World methodology, which requires "
                "every date to be on or after "
                f"{MODERN_MODE_START.isoformat()}."
            )

    for index in range(1, len(sorted_dates)):

        separation_days = (
            sorted_dates[index]
            - sorted_dates[index - 1]
        ).days

        if separation_days < MIN_DATE_SEPARATION_DAYS:
            raise AnalysisValidationError(
                "Trend dates must each be at least "
                f"{MIN_DATE_SEPARATION_DAYS} days apart to "
                "reduce composite-window overlap. "
                f"'{sorted_dates[index - 1].isoformat()}' and "
                f"'{sorted_dates[index].isoformat()}' are too "
                "close together."
            )

    windows = [
        _build_window_metadata(
            single_date
        )
        for single_date in sorted_dates
    ]

    warnings = []

    for single_date, window in zip(
        sorted_dates,
        windows,
    ):

        if window[
            "future_truncated"
        ]:
            warnings.append(
                "The composite window for "
                f"{single_date.isoformat()} extends beyond "
                "today and was truncated to currently "
                "available dates."
            )

    return {
        "latitude":
            latitude,

        "longitude":
            longitude,

        "radius_km":
            radius_km,

        "confidence_threshold":
            confidence_threshold,

        "dates": [
            single_date.isoformat()
            for single_date in sorted_dates
        ],

        "windows":
            windows,

        "warnings":
            warnings,
    }


# ==========================================================
# TREND ANALYSIS
# ==========================================================

def analyze_trend(
    latitude,
    longitude,
    dates,
    radius_km=10,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """
    Analyze land-cover composition independently at each of
    the given dates using the Dynamic World temporal
    consensus methodology.

    Each date is treated as its own standalone period with
    its own valid-pixel mask and coverage percentage. This
    function does NOT calculate pairwise transitions between
    consecutive dates. For that, use the existing pairwise
    Modern analysis (analysis.py) instead.

    Because each period's valid-pixel mask can differ in size
    and location, absolute km2 values are not directly
    comparable across periods when coverage differs
    significantly. For that reason, each period also reports
    composition as a percentage of ITS OWN valid/comparable
    area, and a "reliable" flag indicating whether that
    period's coverage meets the minimum threshold for
    cautious interpretation.

    Observation counts for all periods are retrieved using a
    single combined request, and land-cover statistics for
    all periods are retrieved using a single combined
    reduceRegion request, to avoid one network round trip
    per period.
    """

    request = validate_trend_request(
        latitude=latitude,
        longitude=longitude,
        dates=dates,
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

    period_dates = request[
        "dates"
    ]

    period_windows = request[
        "windows"
    ]

    # ------------------------------------------------------
    # BUILD ONE DYNAMIC WORLD COLLECTION PER PERIOD
    # ------------------------------------------------------

    collections = {}

    for index, window in enumerate(
        period_windows
    ):

        collections[
            f"period_{index}"
        ] = _build_dynamic_world_collection(
            area,
            window,
        )

    # ------------------------------------------------------
    # COMBINED OBSERVATION COUNTS (ONE ROUND TRIP)
    # ------------------------------------------------------

    counts = _get_combined_counts(
        collections
    )

    for index, single_date in enumerate(
        period_dates
    ):

        if counts[
            f"period_{index}"
        ] == 0:
            raise AnalysisDataError(
                "No Dynamic World observations were found "
                f"for {single_date}."
            )

    # ------------------------------------------------------
    # BUILD PER-PERIOD STATISTIC BANDS
    # ------------------------------------------------------

    km2 = (
        ee.Image.pixelArea()
        .divide(1e6)
    )

    stat_bands = []

    for index in range(
        len(period_dates)
    ):

        collection = collections[
            f"period_{index}"
        ]

        consensus = _build_temporal_consensus(
            collection,
            request[
                "confidence_threshold"
            ],
        )

        land = (
            consensus[
                "land"
            ]
            .updateMask(
                consensus[
                    "valid"
                ]
            )
        )

        valid_mask = consensus[
            "valid"
        ]

        vegetation_mask = (
            land.gte(1)
            .And(
                land.lte(5)
            )
        )

        water_mask = land.eq(0)
        built_mask = land.eq(6)
        bare_mask = land.eq(7)

        stat_bands.append(
            km2
            .updateMask(
                valid_mask
            )
            .rename(
                f"period_{index}_valid"
            )
        )

        stat_bands.append(
            km2
            .updateMask(
                vegetation_mask
            )
            .rename(
                f"period_{index}_vegetation"
            )
        )

        stat_bands.append(
            km2
            .updateMask(
                water_mask
            )
            .rename(
                f"period_{index}_water"
            )
        )

        stat_bands.append(
            km2
            .updateMask(
                built_mask
            )
            .rename(
                f"period_{index}_built"
            )
        )

        stat_bands.append(
            km2
            .updateMask(
                bare_mask
            )
            .rename(
                f"period_{index}_bare"
            )
        )

    stats_image = ee.Image.cat(
        stat_bands
    )

    # ------------------------------------------------------
    # COMBINED STATS + TOTAL AREA (ONE ROUND TRIP)
    # ------------------------------------------------------

    try:
        combined = ee.Dictionary(
            {
                "stats":
                    stats_image.reduceRegion(
                        reducer=(
                            ee.Reducer.sum()
                        ),
                        geometry=area,
                        scale=10,
                        maxPixels=1e9,
                        tileScale=4,
                    ),

                "total_area_km2":
                    area
                    .area()
                    .divide(1e6),
            }
        ).getInfo()

    except Exception as error:

        raise AnalysisDataError(
            "Earth Engine could not calculate "
            "trend statistics."
        ) from error

    stats = combined[
        "stats"
    ]

    total_area_km2 = float(
        combined[
            "total_area_km2"
        ]
    )

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

    # ------------------------------------------------------
    # ASSEMBLE PER-PERIOD RESULTS
    # ------------------------------------------------------

    periods = []
    warnings = list(
        request[
            "warnings"
        ]
    )

    for index, (
        single_date,
        window,
    ) in enumerate(
        zip(
            period_dates,
            period_windows,
        )
    ):

        valid_area_km2 = stat_value(
            f"period_{index}_valid"
        )

        if total_area_km2 > 0:
            coverage_percent = (
                valid_area_km2
                / total_area_km2
                * 100
            )

        else:
            coverage_percent = 0.0

        vegetation_km2 = stat_value(
            f"period_{index}_vegetation"
        )

        water_km2 = stat_value(
            f"period_{index}_water"
        )

        built_km2 = stat_value(
            f"period_{index}_built"
        )

        bare_km2 = stat_value(
            f"period_{index}_bare"
        )

        # ------------------------------------------------
        # COMPOSITION AS PERCENT OF THIS PERIOD'S OWN
        # VALID AREA.
        #
        # This is more honest than comparing absolute km2
        # across periods, because each period's valid-pixel
        # mask can differ significantly in size depending on
        # cloud cover, satellite availability and temporal
        # consensus that quarter.
        # ------------------------------------------------

        if valid_area_km2 > 0:

            vegetation_percent_of_valid_area = (
                vegetation_km2
                / valid_area_km2
                * 100
            )

            water_percent_of_valid_area = (
                water_km2
                / valid_area_km2
                * 100
            )

            built_percent_of_valid_area = (
                built_km2
                / valid_area_km2
                * 100
            )

            bare_percent_of_valid_area = (
                bare_km2
                / valid_area_km2
                * 100
            )

        else:

            vegetation_percent_of_valid_area = 0.0
            water_percent_of_valid_area = 0.0
            built_percent_of_valid_area = 0.0
            bare_percent_of_valid_area = 0.0

        reliable = (
            coverage_percent
            >= RELIABLE_COVERAGE_THRESHOLD
        )

        observation_count = counts[
            f"period_{index}"
        ]

        if (
            observation_count
            < LOW_OBSERVATION_WARNING_COUNT
        ):
            warnings.append(
                f"Only {observation_count} Dynamic World "
                f"observation(s) were available for "
                f"{single_date}."
            )

        if coverage_percent < 20:
            warnings.append(
                f"Coverage for {single_date} is very low "
                f"({coverage_percent:.1f}%) and is "
                "insufficient for broad area-level "
                "conclusions at this date."
            )

        elif coverage_percent < 40:
            warnings.append(
                f"Coverage for {single_date} is limited "
                f"({coverage_percent:.1f}%). Conclusions at "
                "this date should be made cautiously."
            )

        periods.append(
            {
                "date":
                    single_date,

                "observations":
                    observation_count,

                "valid_area_km2":
                    valid_area_km2,

                "coverage_percent":
                    coverage_percent,

                "reliable":
                    reliable,

                "vegetation_km2":
                    vegetation_km2,

                "water_km2":
                    water_km2,

                "built_km2":
                    built_km2,

                "bare_km2":
                    bare_km2,

                "vegetation_percent_of_valid_area":
                    vegetation_percent_of_valid_area,

                "water_percent_of_valid_area":
                    water_percent_of_valid_area,

                "built_percent_of_valid_area":
                    built_percent_of_valid_area,

                "bare_percent_of_valid_area":
                    bare_percent_of_valid_area,

                "window":
                    window,
            }
        )

    return {
        "mode":
            "modern_trend",

        "classification_method":
            "dynamic_world_temporal_consensus_"
            "independent_snapshots",

        "methodology_note":
            "Each date is analyzed independently. Coverage "
            "and valid pixels are NOT synchronized across "
            "dates, and no pairwise transition is calculated "
            "between consecutive points. Absolute km2 values "
            "may not be directly comparable across periods "
            "when coverage differs significantly between "
            "them; percent-of-valid-area values and the "
            "'reliable' flag should be used to judge how much "
            "weight to give each point. This trend shows "
            "standalone satellite-derived estimates per date, "
            "not verified step-by-step change evidence.",

        "reliable_coverage_threshold":
            RELIABLE_COVERAGE_THRESHOLD,

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

        "total_area_km2":
            total_area_km2,

        "periods":
            periods,

        "warnings":
            warnings,
    }