"""Convert SetQuery analysis results into report-ready data."""

from datetime import datetime


MODERN_CLASSES = (
    ("Vegetation", "vegetation"),
    ("Built-up", "built"),
    ("Water", "water"),
    ("Bare ground", "bare"),
)

MODERN_TRANSITIONS = (
    ("Vegetation to Built", "vegetation_to_built_km2", "#FF0000"),
    ("Built to Vegetation", "built_to_vegetation_km2", "#00FF00"),
    ("Bare to Built", "bare_to_built_km2", "#FFFF00"),
    ("Non-water to Water", "nonwater_to_water_km2", "#0066FF"),
    ("Water to Non-water", "water_to_nonwater_km2", "#FF8800"),
)


def prepare_report_data(analysis_data):
    """Build a validated, serializable report context."""

    if not isinstance(analysis_data, dict):
        raise ValueError("Analysis data must be a dictionary.")

    required = (
        "mode",
        "result",
        "images",
        "location",
        "latitude",
        "longitude",
        "before_date",
        "after_date",
        "radius_km",
    )

    missing = [
        key for key in required
        if key not in analysis_data
    ]

    if missing:
        raise ValueError(
            "Missing required analysis fields: "
            + ", ".join(missing)
        )

    mode = analysis_data["mode"]
    result = analysis_data["result"]

    if mode not in ("modern_ml", "historical_spectral"):
        raise ValueError("Unsupported report analysis mode.")

    report = {
        "mode": mode,
        "mode_label": analysis_data.get("mode_label", mode),
        "location": str(analysis_data["location"]),
        "latitude": float(analysis_data["latitude"]),
        "longitude": float(analysis_data["longitude"]),
        "before_date": str(analysis_data["before_date"]),
        "after_date": str(analysis_data["after_date"]),
        "radius_km": float(analysis_data["radius_km"]),
        "resolution_m": analysis_data.get("approximate_resolution_m"),
        "total_area_km2": float(result["total_area_km2"]),
        "comparable_area_km2": float(result["comparable_area_km2"]),
        "coverage_percent": float(result["coverage_percent"]),
        "warnings": list(result.get("warnings", [])),
        "images": {
            "before_url": analysis_data["images"].get("before_url"),
            "after_url": analysis_data["images"].get("after_url"),
            "change_url": (
                (analysis_data.get("change_map") or {}).get("change_url")
            ),
        },
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    if mode == "modern_ml":
        report["classes"] = [
            {
                "name": label,
                "before_km2": float(result[f"before_{key}_km2"]),
                "after_km2": float(result[f"after_{key}_km2"]),
            }
            for label, key in MODERN_CLASSES
        ]

        report["transitions"] = [
            {
                "name": label,
                "area_km2": float(result[key]),
                "color": color,
            }
            for label, key, color in MODERN_TRANSITIONS
        ]

        report["observations"] = {
            "before": result.get("before_observations"),
            "after": result.get("after_observations"),
        }

    else:
        report["indices"] = [
            {
                "name": name,
                "before": float(result[f"before_mean_{key}"]),
                "after": float(result[f"after_mean_{key}"]),
                "change": float(result[f"{key}_change"]),
            }
            for name, key in (
                ("NDVI", "ndvi"),
                ("MNDWI", "mndwi"),
                ("NDBI", "ndbi"),
            )
        ]

        report["observations"] = {
            "before": result.get("before_observations"),
            "after": result.get("after_observations"),
        }

    return report
