def get_historical_coverage_level(coverage):
    """
    Interpret comparable Landsat pixel coverage.

    Coverage is not accuracy.
    """

    if coverage >= 70:
        return "GOOD"

    if coverage >= 40:
        return "MODERATE"

    if coverage >= 20:
        return "LIMITED"

    return "VERY LOW"


def _describe_index_change(
    change,
    index_name,
):
    """
    Conservatively describe mean spectral-index change.
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


def generate_historical_summary(
    location,
    before_date,
    after_date,
    result,
):
    """
    Generate a deterministic historical spectral summary.

    Does not translate spectral indices into categorical
    land-cover area without supporting classification.
    """

    coverage = result[
        "coverage_percent"
    ]

    coverage_level = (
        get_historical_coverage_level(
            coverage
        )
    )

    parts = [
        (
            f"SetQuery AI compared Landsat composites "
            f"around {location}, using target dates "
            f"{before_date} and {after_date}. "
            f"Approximately {coverage:.1f}% "
            f"({result['comparable_area_km2']:.2f} km²) "
            f"of the {result['total_area_km2']:.2f} km² "
            f"requested region contained comparable "
            f"valid Landsat pixels. Comparable coverage "
            f"is {coverage_level}."
        ),

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
            "indicator, MNDWI is a water-related spectral "
            "indicator, and NDBI is a built/bare-related "
            "spectral indicator. These index changes are "
            "not direct measurements of vegetation, water "
            "or built-up area."
        ),

        (
            "Historical mode uses Landsat imagery at "
            "approximately 30 m resolution and may compare "
            "different Landsat sensor generations. "
            "Sensor bandpass differences, seasonality, "
            "atmospheric conditions and composite timing "
            "can influence spectral-index values."
        ),
    ]

    if coverage < 20:

        parts.insert(
            1,
            (
                "Comparable coverage is very low and "
                "is insufficient for broad area-level "
                "conclusions."
            ),
        )

    return "\n\n".join(
        parts
    )


def answer_historical_query(
    question,
    result,
):
    """
    Deterministic fallback Q&A for historical mode.
    """

    q = (
        question
        .strip()
        .lower()
    )

    coverage = result[
        "coverage_percent"
    ]

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
            "NDBI responds to built and bare surfaces, "
            "so this result cannot by itself establish "
            "how much urban or built-up area changed."
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
            f"Comparable Landsat coverage is "
            f"{coverage:.1f}% "
            f"({result['comparable_area_km2']:.2f} km²). "
            "Coverage describes usable spatial comparison "
            "and is not an accuracy percentage."
        )

    return (
        f"Historical spectral comparison found mean NDVI "
        f"change of {result['ndvi_change']:+.3f}, mean "
        f"MNDWI change of {result['mndwi_change']:+.3f}, "
        f"and mean NDBI change of "
        f"{result['ndbi_change']:+.3f}. Comparable "
        f"Landsat coverage was {coverage:.1f}%. "
        "These are spectral-index measurements rather "
        "than categorical land-cover area estimates."
    )