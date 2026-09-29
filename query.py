def answer_query(question, result):
    """
    Grounded local fallback for SetQuery AI.

    This function never calls an LLM. It answers only
    from the structured Earth Engine analysis result.
    """

    q = question.lower().strip()

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

    bare_change = (
        result["after_bare_km2"]
        - result["before_bare_km2"]
    )

    coverage = result["coverage_percent"]

    veg_to_built = result[
        "vegetation_to_built_km2"
    ]

    built_to_veg = result[
        "built_to_vegetation_km2"
    ]

    bare_to_built = result[
        "bare_to_built_km2"
    ]

    water_to_land = result[
        "water_to_nonwater_km2"
    ]

    land_to_water = result[
        "nonwater_to_water_km2"
    ]


    def describe_change(
        name,
        value,
    ):

        if abs(value) < 0.001:

            return (
                f"{name} remained approximately stable"
            )

        if value > 0:

            return (
                f"{name} increased by approximately "
                f"{value:.3f} km²"
            )

        return (
            f"{name} decreased by approximately "
            f"{abs(value):.3f} km²"
        )


    def coverage_statement():

        if coverage >= 70:

            quality = "relatively broad"

        elif coverage >= 40:

            quality = "moderate"

        else:

            quality = "limited"

        return (
            f"Comparable coverage is {coverage:.1f}% "
            f"of the requested study area, which provides "
            f"{quality} high-confidence spatial coverage. "
            "Coverage is not an accuracy percentage."
        )


    # =================================================
    # SUMMARY
    # =================================================

    if any(
        phrase in q
        for phrase in [
            "summarize",
            "summary",
            "important changes",
            "main changes",
            "what changed",
            "overall change",
        ]
    ):

        changes = [
            (
                "vegetation",
                vegetation_change,
            ),
            (
                "built-up land",
                built_change,
            ),
            (
                "water",
                water_change,
            ),
            (
                "bare ground",
                bare_change,
            ),
        ]

        largest = max(
            changes,
            key=lambda item: abs(item[1]),
        )

        return (
            f"{describe_change('Vegetation', vegetation_change)}. "
            f"{describe_change('Built-up land', built_change)}. "
            f"{describe_change('Water', water_change)}. "
            f"{describe_change('Bare ground', bare_change)}. "
            f"The largest net class-area difference among these "
            f"categories is for {largest[0]} "
            f"({largest[1]:+.3f} km²). "
            f"High-confidence vegetation → built-up transition "
            f"was {veg_to_built:.4f} km². "
            f"{coverage_statement()} "
            "These are satellite-derived ML estimates."
        )


    # =================================================
    # RELIABILITY / QUALITY
    # =================================================

    if any(
        word in q
        for word in [
            "reliable",
            "reliability",
            "quality",
            "confidence",
            "accurate",
            "accuracy",
            "trust",
        ]
    ):

        return (
            f"{coverage_statement()} "
            f"The analysis used "
            f"{result['before_observations']} ML observations "
            f"around the before period and "
            f"{result['after_observations']} around the after "
            "period. Results should be treated as "
            "satellite-derived ML estimates rather than "
            "surveyed ground truth."
        )


    # =================================================
    # URBAN / BUILT-UP
    # =================================================

    if any(
        term in q
        for term in [
            "built",
            "urban",
            "construction",
            "development",
        ]
    ):

        if (
            "vegetation" in q
            or "converted" in q
            or "transition" in q
        ):

            return (
                f"High-confidence vegetation → built-up "
                f"transition was approximately "
                f"{veg_to_built:.4f} km². "
                f"Built-up → vegetation transition was "
                f"{built_to_veg:.4f} km². "
                "These transition values should not be confused "
                "with the total net built-up area difference."
            )

        return (
            f"{describe_change('Built-up land', built_change)} "
            "within the high-confidence comparable area. "
            f"Vegetation → built-up transition was "
            f"{veg_to_built:.4f} km². "
            f"{coverage_statement()}"
        )


    # =================================================
    # VEGETATION
    # =================================================

    if any(
        term in q
        for term in [
            "vegetation",
            "green",
            "plants",
        ]
    ):

        return (
            f"{describe_change('Vegetation', vegetation_change)} "
            "within the high-confidence comparable area. "
            f"Vegetation → built-up transition was "
            f"{veg_to_built:.4f} km² and built-up → vegetation "
            f"was {built_to_veg:.4f} km²."
        )


    # =================================================
    # WATER
    # =================================================

    if any(
        term in q
        for term in [
            "water",
            "lake",
            "river",
        ]
    ):

        return (
            f"{describe_change('Water', water_change)}. "
            f"Water → non-water transition was "
            f"{water_to_land:.4f} km², while non-water → water "
            f"transition was {land_to_water:.4f} km². "
            "These changes can reflect real land-cover change "
            "or temporal/seasonal water variation."
        )


    # =================================================
    # BARE GROUND
    # =================================================

    if any(
        term in q
        for term in [
            "bare",
            "open land",
            "empty land",
        ]
    ):

        return (
            f"{describe_change('Bare ground', bare_change)}. "
            f"High-confidence bare → built-up transition "
            f"was {bare_to_built:.4f} km²."
        )


    # =================================================
    # ANALYSIS AREA
    # =================================================

    if any(
        term in q
        for term in [
            "area",
            "size",
            "region",
            "coverage",
        ]
    ):

        return (
            f"The requested analysis area is "
            f"{result['total_area_km2']:.2f} km². "
            f"{result['comparable_area_km2']:.2f} km² "
            f"met the confidence requirement in both periods. "
            f"{coverage_statement()}"
        )


    # =================================================
    # LIMITATIONS
    # =================================================

    if any(
        term in q
        for term in [
            "limitation",
            "limitations",
            "cannot tell",
            "can't tell",
            "not tell",
        ]
    ):

        return (
            "This analysis cannot establish why a land-cover "
            "change occurred. It should not be used to claim "
            "specific construction projects, individual buildings, "
            "small roads, disasters or exact property-level change "
            "without additional evidence. Sentinel-2 and the "
            "land-cover model provide area-level estimates, and "
            f"only {coverage:.1f}% of the requested region met "
            "the current confidence requirement in both periods."
        )


    # =================================================
    # FALLBACK
    # =================================================

    return (
        "Gemini is unavailable, so I am using SetQuery AI's "
        "grounded local fallback. I can answer questions about "
        "the overall change summary, vegetation, built-up land, "
        "water, bare ground, detected transitions, analysis area, "
        "data quality and limitations. For example: "
        "'What changed the most?' or "
        "'How reliable is this analysis?'"
    )