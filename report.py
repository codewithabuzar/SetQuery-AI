def generate_analysis_summary(
    location,
    before_date,
    after_date,
    result
):
    coverage = result["coverage_percent"]

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

    if coverage >= 70:
        quality = "good"
    elif coverage >= 40:
        quality = "moderate"
    else:
        quality = "low"

    def direction(value):
        if abs(value) < 0.001:
            return "remained nearly stable"
        elif value > 0:
            return f"increased by approximately {value:.3f} km²"
        else:
            return f"decreased by approximately {abs(value):.3f} km²"

    summary = (
        f"SetQuery AI analyzed {result['total_area_km2']:.2f} km² "
        f"around {location} between {before_date} and {after_date}. "
        f"Approximately {coverage:.1f}% "
        f"({result['comparable_area_km2']:.2f} km²) of the requested "
        f"area met the 60% confidence requirement in both periods, "
        f"giving this analysis {quality} comparable coverage.\n\n"

        f"Within the high-confidence comparable area, vegetation "
        f"{direction(vegetation_change)}, built-up land "
        f"{direction(built_change)}, and water "
        f"{direction(water_change)}.\n\n"

        f"The transition analysis detected approximately "
        f"{result['vegetation_to_built_km2']:.4f} km² of "
        f"vegetation-to-built-up change, "
        f"{result['built_to_vegetation_km2']:.4f} km² of "
        f"built-up-to-vegetation change, "
        f"{result['water_to_nonwater_km2']:.4f} km² of "
        f"water-to-non-water change, and "
        f"{result['nonwater_to_water_km2']:.4f} km² of "
        f"non-water-to-water change.\n\n"

        "These results are satellite-derived machine-learning "
        "estimates rather than surveyed ground truth. Cloud cover, "
        "seasonality, Sentinel-2 spatial resolution and model "
        "confidence can influence the measurements."
    )

    return summary