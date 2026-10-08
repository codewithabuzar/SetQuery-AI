import ee

from analysis import AnalysisDataError


# ==========================================================
# CONFIGURATION
#
# dNBR severity thresholds below follow the widely-cited
# USGS / USFS FIREMON dNBR classification scheme, originally
# calibrated for Landsat. Applied here to Sentinel-2 bands,
# these buckets should be read as an INDICATIVE severity
# category, not a validated, sensor-matched burn severity
# measurement.
# ==========================================================

NBR_NIR_BAND = "B8"
NBR_SWIR_BAND = "B12"

# (lower_bound_exclusive, upper_bound_inclusive, label)
DNBR_SEVERITY_BUCKETS = [
    (-1.0, 0.10, "unburned_or_no_significant_change"),
    (0.10, 0.27, "low_severity"),
    (0.27, 0.44, "moderate_low_severity"),
    (0.44, 0.66, "moderate_high_severity"),
    (0.66, 1.0, "high_severity"),
]


# ==========================================================
# NBR CALCULATION
# ==========================================================

def _compute_nbr(image):
    """
    Compute Normalized Burn Ratio for a single Sentinel-2
    image.

    NBR = (NIR - SWIR) / (NIR + SWIR)
    """

    nir = image.select(NBR_NIR_BAND)
    swir = image.select(NBR_SWIR_BAND)

    return (
        nir.subtract(swir)
        .divide(
            nir.add(swir)
        )
        .rename("nbr")
    )


# ==========================================================
# BURN EVIDENCE FROM SHARED MODERN CONTEXT
# ==========================================================

def analyze_burn_evidence(context):
    """
    Compute NBR-based burn evidence using the Sentinel-2
    collections already built for the shared Modern analysis
    context.

    This reuses context["before_sentinel_collection"] and
    context["after_sentinel_collection"], so no additional
    Sentinel-2 collections are built and no extra observation
    count requests are made.

    This function does NOT claim validated fire detection. It
    reports spectral evidence consistent with vegetation/
    moisture decrease (a possible burn signal) using an
    established but Landsat-calibrated severity classification
    scheme, applied here to Sentinel-2 as an indicative
    category only.
    """

    area = context["area"]

    before_collection = context["before_sentinel_collection"]
    after_collection = context["after_sentinel_collection"]

    before_nbr = (
        before_collection
        .map(_compute_nbr)
        .median()
        .clip(area)
    )

    after_nbr = (
        after_collection
        .map(_compute_nbr)
        .median()
        .clip(area)
    )

    dnbr = (
        before_nbr
        .subtract(after_nbr)
        .rename("dnbr")
    )

    km2 = (
        ee.Image.pixelArea()
        .divide(1e6)
    )

    # ------------------------------------------------------
    # SEVERITY BUCKET AREA BANDS (all summed with one reducer)
    # ------------------------------------------------------

    bucket_bands = []

    for lower, upper, label in DNBR_SEVERITY_BUCKETS:

        bucket_mask = (
            dnbr.gt(lower)
            .And(
                dnbr.lte(upper)
            )
        )

        bucket_bands.append(
            km2
            .updateMask(bucket_mask)
            .rename(label)
        )

    sum_stats_image = ee.Image.cat(
        [
            km2.updateMask(before_nbr.mask()).rename("valid_area"),
        ]
        + bucket_bands
    )

    mean_stats_image = ee.Image.cat(
        [
            before_nbr.rename("before_nbr_mean"),
            after_nbr.rename("after_nbr_mean"),
            dnbr.rename("dnbr_mean"),
        ]
    )

    try:
        combined = ee.Dictionary(
            {
                "sum_stats": sum_stats_image.reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=area,
                    scale=10,
                    maxPixels=1e9,
                    tileScale=4,
                ),

                "mean_stats": mean_stats_image.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=area,
                    scale=10,
                    maxPixels=1e9,
                    tileScale=4,
                ),
            }
        ).getInfo()

    except Exception as error:

        raise AnalysisDataError(
            "Earth Engine could not calculate burn evidence "
            "statistics."
        ) from error

    sum_stats = combined["sum_stats"]
    mean_stats = combined["mean_stats"]

    def stat_value(source, name):
        value = source.get(name)
        if value is None:
            return 0.0
        return float(value)

    valid_area_km2 = stat_value(sum_stats, "valid_area")

    bucket_areas_km2 = {
        label: stat_value(sum_stats, label)
        for _, _, label in DNBR_SEVERITY_BUCKETS
    }

    before_mean_nbr = stat_value(mean_stats, "before_nbr_mean")
    after_mean_nbr = stat_value(mean_stats, "after_nbr_mean")
    mean_dnbr = stat_value(mean_stats, "dnbr_mean")

    warnings = [
        "Burn evidence is based on spectral NBR/dNBR change "
        "and is NOT a validated fire detection or damage "
        "assessment.",
        "Severity categories follow an established Landsat-"
        "calibrated classification scheme, applied here to "
        "Sentinel-2 as an indicative category only.",
        "Vegetation loss from causes other than fire (e.g. "
        "harvesting, construction, drought) can also lower "
        "NBR and should not be assumed to be fire-related "
        "without additional evidence.",
    ]

    if valid_area_km2 <= 0:
        warnings.append(
            "No valid Sentinel-2 pixels were available for "
            "burn evidence calculation in this study area."
        )

    return {
        "method": "sentinel2_nbr_dnbr",
        "nir_band": NBR_NIR_BAND,
        "swir_band": NBR_SWIR_BAND,
        "valid_area_km2": valid_area_km2,
        "before_mean_nbr": before_mean_nbr,
        "after_mean_nbr": after_mean_nbr,
        "mean_dnbr": mean_dnbr,
        "severity_area_km2": bucket_areas_km2,
        "severity_thresholds_note": (
            "dNBR buckets: unburned/no significant change "
            "(<=0.10), low (0.10-0.27), moderate-low "
            "(0.27-0.44), moderate-high (0.44-0.66), high "
            "(>0.66). Source: USGS/USFS FIREMON dNBR scheme, "
            "originally calibrated for Landsat."
        ),
        "warnings": warnings,
    }