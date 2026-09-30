# ==========================================================
# COVERAGE INTERPRETATION
# ==========================================================

def get_historical_coverage_level(
    coverage,
):
    """
    Interpret comparable Landsat spatial coverage.

    Coverage is not accuracy.
    """

    if coverage >= 70:
        return "GOOD"

    if coverage >= 40:
        return "MODERATE"

    if coverage >= 20:
        return "LIMITED"

    return "VERY LOW"


# ==========================================================
# LANDSAT OBSERVATION SUPPORT
# ==========================================================

def get_historical_observation_count(
    sensor_list,
):
    """
    Sum source observations across the Landsat sensors
    used in one comparison period.
    """

    return sum(
        int(
            sensor.get(
                "observations",
                0,
            )
        )
        for sensor in sensor_list
    )


def get_historical_observation_support(
    count,
):
    """
    Interpret temporal source support.

    This is not an accuracy category.
    """

    if count >= 5:
        return "GOOD"

    if count >= 3:
        return "MODERATE"

    if count == 2:
        return "LIMITED"

    return "VERY LOW"


def get_historical_source_support(
    result,
):
    """
    Return BEFORE and AFTER Landsat source-support
    metadata derived from the sensor lists.
    """

    before_count = (
        get_historical_observation_count(
            result.get(
                "before_sensors",
                [],
            )
        )
    )

    after_count = (
        get_historical_observation_count(
            result.get(
                "after_sensors",
                [],
            )
        )
    )

    return {
        "before_count":
            before_count,

        "after_count":
            after_count,

        "before_level":
            get_historical_observation_support(
                before_count
            ),

        "after_level":
            get_historical_observation_support(
                after_count
            ),
    }


def get_historical_support_warnings(
    result,
):
    """
    Generate temporal source-support warnings.

    Spatial comparable coverage and source-observation
    support are deliberately kept separate.
    """

    support = (
        get_historical_source_support(
            result
        )
    )

    warnings = []

    def build_warning(
        period,
        count,
        level,
    ):
        if level == "GOOD":
            return None

        if level == "MODERATE":
            return (
                f"{period} temporal source support is "
                f"MODERATE: only {count} Landsat "
                "observations were available. The "
                "composite has fewer temporal source "
                "observations than preferred."
            )

        if level == "LIMITED":
            return (
                f"{period} temporal source support is "
                f"LIMITED: only {count} Landsat "
                "observations were available. Results "
                "for this period may be sensitive to "
                "individual source scenes."
            )

        if count == 1:
            observation_text = (
                "1 Landsat observation was"
            )
        else:
            observation_text = (
                f"{count} Landsat observations were"
            )

        return (
            f"{period} temporal source support is "
            f"VERY LOW: only {observation_text} "
            "available. Results for this period may be "
            "especially sensitive to the available "
            "source scene(s)."
        )

    before_warning = build_warning(
        "BEFORE",
        support[
            "before_count"
        ],
        support[
            "before_level"
        ],
    )

    after_warning = build_warning(
        "AFTER",
        support[
            "after_count"
        ],
        support[
            "after_level"
        ],
    )

    if before_warning:
        warnings.append(
            before_warning
        )

    if after_warning:
        warnings.append(
            after_warning
        )

    return warnings


# ==========================================================
# INDEX DESCRIPTION
# ==========================================================

def _describe_index_change(
    change,
    index_name,
):
    """
    Conservatively describe a mean spectral-index change.
    """

    magnitude = abs(
        change
    )

    if magnitude < 0.02:
        return (
            f"Mean {index_name} showed a relatively "
            f"small difference ({change:+.3f})."
        )

    if change > 0:
        return (
            f"Mean {index_name} increased by "
            f"{change:.3f}."
        )

    return (
        f"Mean {index_name} decreased by "
        f"{magnitude:.3f}."
    )


# ==========================================================
# DETERMINISTIC HISTORICAL SUMMARY
# ==========================================================

def generate_historical_summary(
    location,
    before_date,
    after_date,
    result,
):
    """
    Generate a grounded deterministic Historical Spectral
    summary.

    Spectral indices are not converted into categorical
    land-cover area measurements.
    """

    coverage = result[
        "coverage_percent"
    ]

    coverage_level = (
        get_historical_coverage_level(
            coverage
        )
    )

    support = (
        get_historical_source_support(
            result
        )
    )

    source_warnings = (
        get_historical_support_warnings(
            result
        )
    )

    parts = [
        (
            "SetQuery AI compared cloud-masked Landsat "
            f"composites around {location}, using target "
            f"dates {before_date} and {after_date}. "
            f"Approximately {coverage:.1f}% "
            f"({result['comparable_area_km2']:.2f} km²) "
            f"of the {result['total_area_km2']:.2f} km² "
            "requested region contained valid comparable "
            "Landsat pixels in both periods. Spatial "
            f"comparable coverage is {coverage_level}."
        ),

        (
            "Temporal source support was "
            f"{support['before_level']} for the BEFORE "
            f"period ({support['before_count']} Landsat "
            "observation(s)) and "
            f"{support['after_level']} for the AFTER "
            f"period ({support['after_count']} Landsat "
            "observation(s))."
        ),
    ]

    if coverage < 20:
        parts.append(
            "Comparable spatial coverage is very low and "
            "is insufficient for broad area-level "
            "conclusions."
        )

    parts.extend(
        source_warnings
    )

    parts.extend(
        [
            _describe_index_change(
                result[
                    "ndvi_change"
                ],
                "NDVI",
            ),

            _describe_index_change(
                result[
                    "mndwi_change"
                ],
                "MNDWI",
            ),

            _describe_index_change(
                result[
                    "ndbi_change"
                ],
                "NDBI",
            ),

            (
                "NDVI is a vegetation-related spectral "
                "indicator, MNDWI is a water-related "
                "spectral indicator, and NDBI is a "
                "built/bare-related spectral indicator. "
                "These index changes are not direct "
                "measurements of vegetation, water, or "
                "built-up area."
            ),

            (
                "Historical mode uses Landsat imagery at "
                "approximately 30 m resolution and may "
                "compare different Landsat sensor "
                "generations. Sensor bandpass differences, "
                "seasonality, atmospheric conditions and "
                "composite timing can influence spectral "
                "index values."
            ),

            (
                "Spatial comparable coverage and temporal "
                "source support are different concepts. "
                "Neither is an accuracy percentage."
            ),
        ]
    )

    return "\n\n".join(
        parts
    )


# ==========================================================
# DETERMINISTIC HISTORICAL Q&A
# ==========================================================

def answer_historical_query(
    question,
    result,
):
    """
    Deterministic grounded Q&A for Historical Spectral mode.
    """

    q = (
        question
        .strip()
        .lower()
    )

    coverage = result[
        "coverage_percent"
    ]

    support = (
        get_historical_source_support(
            result
        )
    )

    if (
        "veget"
        in q
        or "ndvi"
        in q
    ):
        return (
            f"Mean NDVI changed from "
            f"{result['before_mean_ndvi']:.3f} to "
            f"{result['after_mean_ndvi']:.3f}, a "
            f"difference of {result['ndvi_change']:+.3f}. "
            "NDVI is a vegetation-related spectral "
            "indicator; this should not be interpreted "
            "as a direct vegetation-area measurement."
        )

    if (
        "water"
        in q
        or "mndwi"
        in q
    ):
        return (
            f"Mean MNDWI changed from "
            f"{result['before_mean_mndwi']:.3f} to "
            f"{result['after_mean_mndwi']:.3f}, a "
            f"difference of "
            f"{result['mndwi_change']:+.3f}. "
            "MNDWI is a water-related spectral indicator, "
            "not a direct measurement of water area."
        )

    if (
        "built"
        in q
        or "urban"
        in q
        or "ndbi"
        in q
    ):
        return (
            f"Mean NDBI changed from "
            f"{result['before_mean_ndbi']:.3f} to "
            f"{result['after_mean_ndbi']:.3f}, a "
            f"difference of {result['ndbi_change']:+.3f}. "
            "NDBI responds to both built and bare "
            "surfaces, so this result cannot by itself "
            "establish how much urban or built-up area "
            "changed."
        )

    if (
        "observation"
        in q
        or "source"
        in q
    ):
        return (
            "Landsat temporal source support was "
            f"{support['before_level']} for the BEFORE "
            f"period ({support['before_count']} "
            "observation(s)) and "
            f"{support['after_level']} for the AFTER "
            f"period ({support['after_count']} "
            "observation(s)). Source support is not "
            "an accuracy percentage."
        )

    if (
        "coverage"
        in q
        or "quality"
        in q
        or "reliable"
        in q
    ):
        return (
            f"Comparable Landsat spatial coverage is "
            f"{coverage:.1f}% "
            f"({result['comparable_area_km2']:.2f} km²). "
            "BEFORE temporal source support is "
            f"{support['before_level']} and AFTER support "
            f"is {support['after_level']}. Spatial "
            "coverage and source support are different "
            "quality indicators, and neither is an "
            "accuracy percentage."
        )

    return (
        "Historical spectral comparison found mean NDVI "
        f"change of {result['ndvi_change']:+.3f}, mean "
        f"MNDWI change of {result['mndwi_change']:+.3f}, "
        f"and mean NDBI change of "
        f"{result['ndbi_change']:+.3f}. Comparable "
        f"Landsat spatial coverage was {coverage:.1f}%. "
        "BEFORE/AFTER temporal source support was "
        f"{support['before_level']} / "
        f"{support['after_level']}. These are spectral "
        "measurements rather than categorical land-cover "
        "area estimates."
    )