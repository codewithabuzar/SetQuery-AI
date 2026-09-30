# ==========================================================
# MODERN ML COVERAGE INTERPRETATION
# ==========================================================

def get_coverage_interpretation(
    coverage,
):
    """
    Interpret temporal-consensus comparable coverage.

    Coverage is NOT classification accuracy.

    It represents the portion of the requested study area
    where both analysis periods passed the configured
    Dynamic World temporal-consensus rules.
    """

    if coverage >= 70:

        return {
            "level":
                "GOOD",

            "description":
                (
                    "Broad temporal-consensus comparable "
                    "coverage is available, although the "
                    "results remain satellite-derived ML "
                    "estimates."
                ),
        }

    if coverage >= 40:

        return {
            "level":
                "MODERATE",

            "description":
                (
                    "A substantial portion of the requested "
                    "area is comparable, but conclusions "
                    "should not be assumed to represent "
                    "pixels excluded by the temporal-"
                    "consensus filters."
                ),
        }

    if coverage >= 20:

        return {
            "level":
                "LIMITED",

            "description":
                (
                    "Only a limited portion of the requested "
                    "area is temporally comparable. "
                    "Area-wide conclusions should be made "
                    "cautiously."
                ),
        }

    return {
        "level":
            "VERY LOW",

        "description":
            (
                "Temporal-consensus comparable coverage "
                "is insufficient for broad area-level "
                "conclusions about the requested study "
                "region."
            ),
    }


# ==========================================================
# AUTOMATIC DETERMINISTIC SUMMARY
# ==========================================================

def generate_analysis_summary(
    location,
    before_date,
    after_date,
    result,
):
    """
    Generate a deterministic Modern ML analysis summary.

    This function does not use an LLM.
    """

    coverage = result[
        "coverage_percent"
    ]

    coverage_info = (
        get_coverage_interpretation(
            coverage
        )
    )

    vegetation_change = (
        result[
            "after_vegetation_km2"
        ]
        -
        result[
            "before_vegetation_km2"
        ]
    )

    built_change = (
        result[
            "after_built_km2"
        ]
        -
        result[
            "before_built_km2"
        ]
    )

    water_change = (
        result[
            "after_water_km2"
        ]
        -
        result[
            "before_water_km2"
        ]
    )

    confidence_threshold = result.get(
        "confidence_threshold",
        0.60,
    )

    min_confident_observations = result.get(
        "min_confident_observations",
        2,
    )

    min_confidence_frequency = result.get(
        "min_confidence_frequency",
        0.50,
    )

    min_temporal_consensus = result.get(
        "min_temporal_consensus",
        0.60,
    )

    def direction(
        value,
    ):
        """
        Describe net class-area difference.
        """

        if abs(value) < 0.001:

            return (
                "showed little net difference"
            )

        if value > 0:

            return (
                "increased by approximately "
                f"{value:.3f} km²"
            )

        return (
            "decreased by approximately "
            f"{abs(value):.3f} km²"
        )

    parts = []

    parts.append(
        (
            "SetQuery AI analyzed a requested area of "
            f"{result['total_area_km2']:.2f} km² around "
            f"{location}, comparing target dates "
            f"{before_date} and {after_date}. "
            f"Approximately {coverage:.1f}% "
            f"({result['comparable_area_km2']:.2f} km²) "
            "of the requested area passed the configured "
            "Dynamic World temporal-consensus rules in "
            "both periods. Comparable coverage is "
            f"{coverage_info['level']}."
        )
    )

    parts.append(
        coverage_info[
            "description"
        ]
    )

    parts.append(
        (
            "Within the temporal-consensus comparable "
            "subset, vegetation "
            f"{direction(vegetation_change)}, "
            "built-up land "
            f"{direction(built_change)}, and water "
            f"{direction(water_change)}."
        )
    )

    if coverage < 20:

        parts.append(
            (
                "Because comparable coverage is very low, "
                "these net differences describe only the "
                "small comparable subset and should not be "
                "interpreted as evidence that the wider "
                "requested study area was stable or changed "
                "by the same amounts."
            )
        )

    parts.append(
        (
            "Within the comparable subset, the transition "
            "analysis detected approximately "
            f"{result['vegetation_to_built_km2']:.4f} km² "
            "of vegetation-to-built-up transition, "
            f"{result['built_to_vegetation_km2']:.4f} km² "
            "of built-up-to-vegetation transition, "
            f"{result['bare_to_built_km2']:.4f} km² "
            "of bare-to-built-up transition, "
            f"{result['water_to_nonwater_km2']:.4f} km² "
            "of water-to-non-water transition, and "
            f"{result['nonwater_to_water_km2']:.4f} km² "
            "of non-water-to-water transition."
        )
    )

    parts.append(
        (
            "A pixel is considered valid within a period "
            "only when individual Dynamic World "
            f"observations reach at least "
            f"{confidence_threshold * 100:.0f}% maximum "
            "class probability, at least "
            f"{min_confident_observations} confident "
            "observations are available, at least "
            f"{min_confidence_frequency * 100:.0f}% of "
            "available observations are confident, and "
            f"at least "
            f"{min_temporal_consensus * 100:.0f}% of the "
            "confident classifications agree on the "
            "dominant class. A pixel enters the comparison "
            "only when both periods pass these rules."
        )
    )

    parts.append(
        (
            "Comparable coverage is not an accuracy "
            "percentage. It describes the spatial portion "
            "of the requested region satisfying these "
            "temporal-consensus requirements."
        )
    )

    parts.append(
        (
            "These measurements are satellite-derived "
            "machine-learning estimates rather than "
            "surveyed ground truth. Cloud cover, "
            "seasonality, Sentinel-2 spatial resolution, "
            "composite timing and Dynamic World "
            "classification behavior can influence the "
            "results."
        )
    )

    return "\n\n".join(
        parts
    )