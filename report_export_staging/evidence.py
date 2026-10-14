"""On-demand supplementary evidence for SetQuery PDF reports."""

from analysis import prepare_modern_analysis

from burn_analysis import analyze_burn_evidence
from vegetation_stress_analysis import analyze_vegetation_stress
from flood_analysis import analyze_flood_evidence


EVIDENCE_OPTIONS = (
    "burn",
    "vegetation",
    "flood",
)


def collect_selected_evidence(
    analysis_data,
    selected,
    existing=None,
    progress=None,
):
    """
    Calculate only selected supplementary analyses.

    Existing results are reused when supplied.

    Returns a dictionary containing selected evidence.
    """

    selected = set(selected or [])

    unknown = selected - set(EVIDENCE_OPTIONS)

    if unknown:
        raise ValueError(
            "Unknown evidence options: "
            + ", ".join(sorted(unknown))
        )

    if not selected:
        return {}

    if analysis_data["mode"] != "modern_ml":
        raise ValueError(
            "Supplementary evidence is currently supported "
            "only for Modern ML reports."
        )

    existing = existing or {}

    def notify(message):
        if progress:
            progress(message)

    results = {}

    modern_context = None

    # Build shared context only if Burn/Vegetation requires
    # fresh calculation.
    needs_context = any(
        option in selected and existing.get(option) is None
        for option in ("burn", "vegetation")
    )

    if needs_context:
        notify("Preparing Sentinel-2 evidence collections...")

        modern_context = prepare_modern_analysis(
            latitude=analysis_data["latitude"],
            longitude=analysis_data["longitude"],
            before_date=analysis_data["before_date"],
            after_date=analysis_data["after_date"],
            radius_km=analysis_data["radius_km"],
        )

    if "burn" in selected:

        if existing.get("burn") is not None:
            results["burn"] = existing["burn"]
        else:
            notify("Calculating NBR/dNBR burn evidence...")
            results["burn"] = analyze_burn_evidence(
                modern_context
            )

    if "vegetation" in selected:

        if existing.get("vegetation") is not None:
            results["vegetation"] = existing["vegetation"]
        else:
            notify("Calculating NDVI vegetation stress...")
            results["vegetation"] = analyze_vegetation_stress(
                modern_context
            )

    if "flood" in selected:

        if existing.get("flood") is not None:
            results["flood"] = existing["flood"]
        else:
            notify("Calculating Sentinel-1 SAR flood evidence...")
            results["flood"] = analyze_flood_evidence(
                latitude=analysis_data["latitude"],
                longitude=analysis_data["longitude"],
                before_date=analysis_data["before_date"],
                after_date=analysis_data["after_date"],
                radius_km=analysis_data["radius_km"],
            )

    return results
