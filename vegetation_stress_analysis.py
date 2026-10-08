import ee

from analysis import AnalysisDataError


# ==========================================================
# CONFIGURATION
# ==========================================================

NDVI_NIR_BAND = "B8"
NDVI_RED_BAND = "B4"

# A small threshold to avoid labeling negligible noise-level
# NDVI differences as a meaningful increase or decrease.
NDVI_CHANGE_NOISE_THRESHOLD = 0.05


# ==========================================================
# NDVI CALCULATION
# ==========================================================

def _compute_ndvi(image):
    """
    Compute Normalized Difference Vegetation Index for a
    single Sentinel-2 image.

    NDVI = (NIR - RED) / (NIR + RED)
    """

    nir = image.select(NDVI_NIR_BAND)
    red = image.select(NDVI_RED_BAND)

    return (
        nir.subtract(red)
        .divide(
            nir.add(red)
        )
        .rename("ndvi")
    )


# ==========================================================
# VEGETATION STRESS FROM SHARED MODERN CONTEXT
# ==========================================================

def analyze_vegetation_stress(context):
    """
    Compute NDVI-based vegetation greenness change using the
    Sentinel-2 collections already built for the shared
    Modern analysis context.

    This reuses context["before_sentinel_collection"] and
    context["after_sentinel_collection"], so no additional
    Sentinel-2 collections are built and no extra observation
    count requests are made.

    This function does NOT claim validated drought detection
    or crop stress confirmation. It reports spectral evidence
    of vegetation greenness/vigor change (NDVI), which can
    result from many causes including seasonal variation,
    rainfall, land management, or land-cover conversion.
    """

    area = context["area"]

    before_collection = context["before_sentinel_collection"]
    after_collection = context["after_sentinel_collection"]

    before_ndvi = (
        before_collection
        .map(_compute_ndvi)
        .median()
        .clip(area)
    )

    after_ndvi = (
        after_collection
        .map(_compute_ndvi)
        .median()
        .clip(area)
    )

    ndvi_change = (
        after_ndvi
        .subtract(before_ndvi)
        .rename("ndvi_change")
    )

    km2 = (
        ee.Image.pixelArea()
        .divide(1e6)
    )

    decreased_mask = ndvi_change.lt(
        -NDVI_CHANGE_NOISE_THRESHOLD
    )

    increased_mask = ndvi_change.gt(
        NDVI_CHANGE_NOISE_THRESHOLD
    )

    stable_mask = (
        ndvi_change
        .gte(-NDVI_CHANGE_NOISE_THRESHOLD)
        .And(
            ndvi_change.lte(NDVI_CHANGE_NOISE_THRESHOLD)
        )
    )

    sum_stats_image = ee.Image.cat(
        [
            km2.updateMask(before_ndvi.mask()).rename("valid_area"),
            km2.updateMask(decreased_mask).rename("decreased_area"),
            km2.updateMask(increased_mask).rename("increased_area"),
            km2.updateMask(stable_mask).rename("stable_area"),
        ]
    )

    mean_stats_image = ee.Image.cat(
        [
            before_ndvi.rename("before_ndvi_mean"),
            after_ndvi.rename("after_ndvi_mean"),
            ndvi_change.rename("ndvi_change_mean"),
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
            "Earth Engine could not calculate vegetation "
            "stress statistics."
        ) from error

    sum_stats = combined["sum_stats"]
    mean_stats = combined["mean_stats"]

    def stat_value(source, name):
        value = source.get(name)
        if value is None:
            return 0.0
        return float(value)

    valid_area_km2 = stat_value(sum_stats, "valid_area")
    decreased_area_km2 = stat_value(sum_stats, "decreased_area")
    increased_area_km2 = stat_value(sum_stats, "increased_area")
    stable_area_km2 = stat_value(sum_stats, "stable_area")

    before_mean_ndvi = stat_value(mean_stats, "before_ndvi_mean")
    after_mean_ndvi = stat_value(mean_stats, "after_ndvi_mean")
    mean_ndvi_change = stat_value(mean_stats, "ndvi_change_mean")

    if valid_area_km2 > 0:
        decreased_percent = decreased_area_km2 / valid_area_km2 * 100
        increased_percent = increased_area_km2 / valid_area_km2 * 100
        stable_percent = stable_area_km2 / valid_area_km2 * 100
    else:
        decreased_percent = 0.0
        increased_percent = 0.0
        stable_percent = 0.0

    warnings = [
        "Vegetation greenness change (NDVI) is spectral "
        "evidence, not a validated drought or crop-stress "
        "confirmation.",
        "NDVI change can result from many causes including "
        "seasonal variation, rainfall differences, land "
        "management, or land-cover conversion, not only "
        "vegetation health decline.",
    ]

    if valid_area_km2 <= 0:
        warnings.append(
            "No valid Sentinel-2 pixels were available for "
            "vegetation stress calculation in this study area."
        )

    return {
        "method": "sentinel2_ndvi_change",
        "nir_band": NDVI_NIR_BAND,
        "red_band": NDVI_RED_BAND,
        "valid_area_km2": valid_area_km2,
        "before_mean_ndvi": before_mean_ndvi,
        "after_mean_ndvi": after_mean_ndvi,
        "mean_ndvi_change": mean_ndvi_change,
        "decreased_area_km2": decreased_area_km2,
        "increased_area_km2": increased_area_km2,
        "stable_area_km2": stable_area_km2,
        "decreased_percent": decreased_percent,
        "increased_percent": increased_percent,
        "stable_percent": stable_percent,
        "noise_threshold": NDVI_CHANGE_NOISE_THRESHOLD,
        "warnings": warnings,
    }