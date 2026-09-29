def answer_query(question, result):
    """
    Answer questions using only calculated
    SetQuery AI analysis results.
    """

    q = question.lower().strip()

    # -------------------------------------------------
    # CALCULATED DIFFERENCES
    # -------------------------------------------------

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

    coverage = result[
        "coverage_percent"
    ]

    # -------------------------------------------------
    # VEGETATION
    # -------------------------------------------------

    if (
        "vegetation" in q
        and
        ("increase" in q or "decrease" in q or "change" in q)
    ):

        if abs(vegetation_change) < 0.001:

            return (
                "Vegetation remained approximately stable "
                "within the high-confidence comparable area."
            )

        elif vegetation_change > 0:

            return (
                "Vegetation increased by approximately "
                f"{vegetation_change:.3f} km² within the "
                "high-confidence comparable area."
            )

        else:

            return (
                "Vegetation decreased by approximately "
                f"{abs(vegetation_change):.3f} km² within "
                "the high-confidence comparable area."
            )

    # -------------------------------------------------
    # BUILT-UP / URBAN
    # -------------------------------------------------

    if (
        "built" in q
        or
        "urban" in q
        or
        "construction" in q
    ):

        if (
            "vegetation" in q
            and
            (
                "became" in q
                or
                "converted" in q
                or
                "transition" in q
            )
        ):

            amount = result[
                "vegetation_to_built_km2"
            ]

            return (
                "Approximately "
                f"{amount:.4f} km² was classified as "
                "high-confidence vegetation → built-up "
                "transition."
            )

        if abs(built_change) < 0.001:

            return (
                "Built-up land remained approximately "
                "stable within the high-confidence "
                "comparable area."
            )

        elif built_change > 0:

            return (
                "Built-up land increased by approximately "
                f"{built_change:.3f} km² within the "
                "high-confidence comparable area."
            )

        else:

            return (
                "Built-up land decreased by approximately "
                f"{abs(built_change):.3f} km² within the "
                "high-confidence comparable area."
            )

    # -------------------------------------------------
    # WATER
    # -------------------------------------------------

    if "water" in q:

        if (
            "non-water" in q
            or
            "new water" in q
        ):

            amount = result[
                "nonwater_to_water_km2"
            ]

            return (
                "Approximately "
                f"{amount:.4f} km² was classified as "
                "non-water → water transition."
            )

        if abs(water_change) < 0.001:

            return (
                "Water coverage remained approximately "
                "stable within the high-confidence "
                "comparable area."
            )

        elif water_change > 0:

            return (
                "Water coverage increased by approximately "
                f"{water_change:.3f} km²."
            )

        else:

            return (
                "Water coverage decreased by approximately "
                f"{abs(water_change):.3f} km²."
            )

    # -------------------------------------------------
    # QUALITY / CONFIDENCE
    # -------------------------------------------------

    if (
        "reliable" in q
        or
        "quality" in q
        or
        "confidence" in q
        or
        "accuracy" in q
    ):

        if coverage >= 70:

            label = "good"

        elif coverage >= 40:

            label = "moderate"

        else:

            label = "low"

        return (
            f"Comparable coverage is {coverage:.1f}%, "
            f"which the current SetQuery AI interface "
            f"labels as {label}. This is not an accuracy "
            "percentage. It means that this proportion of "
            "the requested region passed the 60% ML "
            "confidence threshold in both periods."
        )

    # -------------------------------------------------
    # AREA
    # -------------------------------------------------

    if (
        "area" in q
        or
        "size" in q
    ):

        return (
            "The requested analysis region covers "
            f"{result['total_area_km2']:.2f} km². "
            f"{result['comparable_area_km2']:.2f} km² "
            "met the confidence requirement in both "
            "periods."
        )

    # -------------------------------------------------
    # FALLBACK
    # -------------------------------------------------

    return (
        "I can currently answer questions about "
        "vegetation, built-up/urban land, water, "
        "detected transitions, analysis area, and "
        "data confidence. Try asking: "
        "'Did built-up land increase?'"
    )