def get_coverage_interpretation(coverage):
    """
    Interpret comparable spatial coverage.

    Coverage is NOT classification accuracy.
    It is the percentage of the requested region where
    both periods satisfy the configured confidence rule.
    """

    if coverage >= 70:
        return {
            "level": "GOOD",
            "description": (
                "Broad comparable coverage is available, although "
                "the results remain satellite-derived ML estimates."
            ),
        }

    if coverage >= 40:
        return {
            "level": "MODERATE",
            "description": (
                "A substantial portion of the requested area is "
                "comparable, but conclusions should not be assumed "
                "to represent areas excluded by the confidence filter."
            ),
        }

    if coverage >= 20:
        return {
            "level": "LIMITED",
            "description": (
                "Only a limited portion of the requested area is "
                "comparable. Area-wide conclusions should be made "
                "cautiously."
            ),
        }

    return {
        "level": "VERY LOW",
        "description": (
            "Comparable coverage is insufficient for broad "
            "area-level conclusions about the requested study region."
        ),
    }


def generate_analysis_summary(
    location,
    before_date,
    after_date,
    result,
):
    coverage = result["coverage_percent"]

    coverage_info = get_coverage_interpretation(
        coverage
    )

    vegetation_change = (
        result["after_vegetation_km2"]
        - result["before_vegetation_km2"]
    )

    built_change = (
        result["after_built_km2"]
        - result["before_built_km2"]
    )

    water_change = (
        result["after_water_km2"]
        - result["before_water_km2"]
    )

    def direction(value):
        if abs(value) < 0.001:
            return "showed little net difference"

        if value > 0:
            return (
                f"increased by approximately "
                f"{value:.3f} km²"
            )

        return (
            f"decreased by approximately "
            f"{abs(value):.3f} km²"
        )

    summary_parts = []

    summary_parts.append(
        f"SetQuery AI analyzed a requested area of "
        f"{result['total_area_km2']:.2f} km² around "
        f"{location}, comparing target dates "
        f"{before_date} and {after_date}. "
        f"Approximately {coverage:.1f}% "
        f"({result['comparable_area_km2']:.2f} km²) "
        f"of the requested area met the 60% confidence "
        f"requirement in both periods. "
        f"Comparable coverage is "
        f"{coverage_info['level']}."
    )

    summary_parts.append(
        coverage_info["description"]
    )

    summary_parts.append(
        f"Within the high-confidence comparable subset, "
        f"vegetation {direction(vegetation_change)}, "
        f"built-up land {direction(built_change)}, "
        f"and water {direction(water_change)}."
    )

    # Extra protection against over-interpreting very
    # low spatial coverage.
    if coverage < 20:
        summary_parts.append(
            "Because comparable coverage is very low, "
            "these net differences describe only the "
            "small comparable subset and should not be "
            "interpreted as evidence that the wider "
            "requested study area was stable or changed "
            "by the same amounts."
        )

    summary_parts.append(
        f"Within the comparable subset, the transition "
        f"analysis detected approximately "
        f"{result['vegetation_to_built_km2']:.4f} km² "
        f"of vegetation-to-built-up transition, "
        f"{result['built_to_vegetation_km2']:.4f} km² "
        f"of built-up-to-vegetation transition, "
        f"{result['bare_to_built_km2']:.4f} km² "
        f"of bare-to-built-up transition, "
        f"{result['water_to_nonwater_km2']:.4f} km² "
        f"of water-to-non-water transition, and "
        f"{result['nonwater_to_water_km2']:.4f} km² "
        f"of non-water-to-water transition."
    )

    summary_parts.append(
        "Coverage is not an accuracy percentage. "
        "It represents the portion of the requested "
        "study area where both periods met the configured "
        "Dynamic World ML confidence threshold."
    )

    summary_parts.append(
        "These measurements are satellite-derived "
        "machine-learning estimates rather than surveyed "
        "ground truth. Cloud cover, seasonality, "
        "Sentinel-2 spatial resolution, composite timing "
        "and model confidence can influence the results."
    )

    return "\n\n".join(summary_parts)