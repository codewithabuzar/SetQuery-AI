"""
Flood Evidence (Sentinel-1 SAR) — surface-water change indicator.

METHODOLOGY NOTES (read before using results):

- Uses Sentinel-1 SAR backscatter (VV polarization) to flag likely NEW
  standing water between a Before and After period.
- This is NOT a validated flood damage assessment. It is a radar-based
  change indicator only.
- Water/non-water separation uses Otsu's automatic thresholding method
  applied to the After-period VV backscatter histogram. This is the
  approach documented in Google Earth Engine's own community tutorial
  for SAR flood mapping, rather than a fixed or arbitrary dB cutoff.
- The SAME threshold is applied to both the Before and After images so
  that "new water" reflects where backscatter crossed that same water/
  land boundary between periods, not a difference in illumination.
- Permanent water bodies (JRC Global Surface Water, occurrence >= 50%)
  are excluded, so results describe NEW water presence, not existing
  lakes, rivers, or ponds.
- SAR backscatter depends on viewing geometry (orbit pass). Before/After
  images are filtered to the SAME relative orbit where possible. If no
  shared orbit exists, a warning is included and the comparison is less
  reliable.
- Steep terrain (> 5 degree slope, from SRTM) is excluded because radar
  layover and shadow effects can mimic water signatures there.
- A focal-median speckle filter is applied, but SAR speckle noise is
  never fully eliminated. Small isolated flagged pixels should not be
  over-interpreted as confirmed flooding.
"""

import ee


SENTINEL1_MIN_DATE = "2014-10-01"
COMPOSITE_WINDOW_DAYS = 15
MIN_DATE_SEPARATION_DAYS = 90
PERMANENT_WATER_OCCURRENCE_THRESHOLD = 50  # percent, JRC GSW "occurrence" band
SLOPE_MASK_DEGREES = 5
OTSU_HISTOGRAM_BUCKETS = 255


class FloodValidationError(Exception):
    """Raised for invalid user input (dates, etc.)."""


class FloodDataError(Exception):
    """Raised when Earth Engine cannot supply usable data."""


def _ensure_ee_initialized():
    """Initialize Earth Engine if it has not been initialized yet."""
    try:
        ee.Number(1).getInfo()
    except Exception:
        try:
            ee.Initialize(project="optimum-reactor-510109-b5")
        except Exception as error:
            raise FloodDataError(
                f"Earth Engine could not be initialized: {error}"
            ) from error


def _build_sentinel1_collection(aoi, start, end):
    """Sentinel-1 GRD, IW mode, VV polarization, within the AOI and window."""
    return (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi)
        .filterDate(start, end)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .select("VV")
    )


def _pick_shared_orbit(before_orbits, after_orbits):
    """
    Given plain Python lists of relativeOrbitNumber_start values,
    return the orbit shared between both periods with the most
    combined images, or None if no orbit is shared.
    """
    if not before_orbits or not after_orbits:
        return None

    shared = set(before_orbits) & set(after_orbits)

    if not shared:
        return None

    return max(
        shared,
        key=lambda orbit: before_orbits.count(orbit) + after_orbits.count(orbit),
    )


def _otsu_threshold(histogram_dict):
    """
    Compute Otsu's automatic threshold from an Earth Engine histogram
    dictionary (as returned by ee.Reducer.histogram()).

    This finds the backscatter value that best separates the histogram
    into two classes (water / non-water) by maximizing between-class
    variance. This is the method documented in Google Earth Engine's
    community tutorial for SAR flood mapping.
    """
    histogram_dict = ee.Dictionary(histogram_dict)
    counts = ee.Array(histogram_dict.get("histogram"))
    means = ee.Array(histogram_dict.get("bucketMeans"))
    size = means.length().get([0])
    total = counts.reduce(ee.Reducer.sum(), [0]).get([0])
    sum_value = means.multiply(counts).reduce(ee.Reducer.sum(), [0]).get([0])
    mean = sum_value.divide(total)

    indices = ee.List.sequence(1, size)

    def between_class_variance(i):
        a_counts = counts.slice(0, 0, i)
        a_count = a_counts.reduce(ee.Reducer.sum(), [0]).get([0])
        a_means = means.slice(0, 0, i)
        a_mean = (
            a_means.multiply(a_counts)
            .reduce(ee.Reducer.sum(), [0])
            .get([0])
            .divide(a_count)
        )
        b_count = total.subtract(a_count)
        b_mean = sum_value.subtract(a_count.multiply(a_mean)).divide(b_count)
        return a_count.multiply(a_mean.subtract(mean).pow(2)).add(
            b_count.multiply(b_mean.subtract(mean).pow(2))
        )

    bss = ee.Array(indices.map(between_class_variance))
    return means.sort(bss).get([-1])


def analyze_flood_evidence(latitude, longitude, before_date, after_date, radius_km):
    """
    Compute SAR-based new-surface-water evidence between two dates.

    Returns a dictionary of measurements and warnings. Raises only on
    genuine input or data problems, never on "no flood detected".
    """

    _ensure_ee_initialized()

    before_date_obj = ee.Date(before_date)
    after_date_obj = ee.Date(after_date)

    separation_days = after_date_obj.difference(before_date_obj, "day").getInfo()

    if separation_days < MIN_DATE_SEPARATION_DAYS:
        raise FloodValidationError(
            f"Before and After dates must be at least {MIN_DATE_SEPARATION_DAYS} "
            "days apart for flood evidence analysis."
        )

    aoi = ee.Geometry.Point([longitude, latitude]).buffer(radius_km * 1000)

    before_start = before_date_obj.advance(-COMPOSITE_WINDOW_DAYS, "day")
    before_end = before_date_obj.advance(COMPOSITE_WINDOW_DAYS, "day")
    after_start = after_date_obj.advance(-COMPOSITE_WINDOW_DAYS, "day")
    after_end = after_date_obj.advance(COMPOSITE_WINDOW_DAYS, "day")

    before_collection = _build_sentinel1_collection(aoi, before_start, before_end)
    after_collection = _build_sentinel1_collection(aoi, after_start, after_end)

    orbit_info = ee.Dictionary({
        "before_orbits": before_collection.aggregate_array("relativeOrbitNumber_start"),
        "after_orbits": after_collection.aggregate_array("relativeOrbitNumber_start"),
    }).getInfo()

    before_orbits = orbit_info["before_orbits"]
    after_orbits = orbit_info["after_orbits"]

    if not before_orbits or not after_orbits:
        raise FloodDataError(
            "No Sentinel-1 SAR imagery was found for one or both periods "
            "in this area. Try a wider date range or a different location."
        )

    warnings = []
    shared_orbit = _pick_shared_orbit(before_orbits, after_orbits)

    if shared_orbit is not None:
        before_collection = before_collection.filter(
            ee.Filter.eq("relativeOrbitNumber_start", shared_orbit)
        )
        after_collection = after_collection.filter(
            ee.Filter.eq("relativeOrbitNumber_start", shared_orbit)
        )
        orbit_matched = True
        before_observations = before_orbits.count(shared_orbit)
        after_observations = after_orbits.count(shared_orbit)
    else:
        orbit_matched = False
        before_observations = len(before_orbits)
        after_observations = len(after_orbits)
        warnings.append(
            "No shared Sentinel-1 orbit pass was found between the Before "
            "and After periods. Results may be affected by viewing-geometry "
            "differences rather than real surface change."
        )

    speckle_kernel = ee.Kernel.square(radius=1)

    before_image = (
        before_collection.median()
        .focal_median(kernel=speckle_kernel, iterations=1)
        .clip(aoi)
    )
    after_image = (
        after_collection.median()
        .focal_median(kernel=speckle_kernel, iterations=1)
        .clip(aoi)
    )

    gsw_occurrence = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")
    permanent_water_free_mask = (
        gsw_occurrence.gte(PERMANENT_WATER_OCCURRENCE_THRESHOLD)
        .unmask(0)
        .Not()
        .rename("flood")
    )

    dem = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(dem)
    terrain_ok_mask = slope.lt(SLOPE_MASK_DEGREES).rename("flood")

    after_histogram = after_image.reduceRegion(
        reducer=ee.Reducer.histogram(OTSU_HISTOGRAM_BUCKETS, 2),
        geometry=aoi,
        scale=10,
        maxPixels=1e9,
        bestEffort=True,
    ).get("VV")

    otsu_threshold = _otsu_threshold(after_histogram)

    before_water_mask = before_image.lt(otsu_threshold).rename("flood")
    after_water_mask = after_image.lt(otsu_threshold).rename("flood")

    new_water_mask = (
        after_water_mask
        .And(before_water_mask.Not())
        .And(permanent_water_free_mask)
        .And(terrain_ok_mask)
        .rename("flood")
    )

    pixel_area = ee.Image.pixelArea()

    new_water_area_image = new_water_mask.multiply(pixel_area).rename("new_water_area")
    valid_area_image = terrain_ok_mask.multiply(pixel_area).rename("valid_area")

    diff_mean = after_image.subtract(before_image).rename("vv_diff").reduceRegion(
        reducer=ee.Reducer.mean(), geometry=aoi, scale=10, maxPixels=1e9, bestEffort=True
    ).get("vv_diff")

    final_results = ee.Dictionary({
        "before_mean_vv": before_image.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=aoi, scale=10, maxPixels=1e9, bestEffort=True
        ).get("VV"),
        "after_mean_vv": after_image.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=aoi, scale=10, maxPixels=1e9, bestEffort=True
        ).get("VV"),
        "mean_vv_difference": diff_mean,
        "otsu_threshold": otsu_threshold,
        "new_water_area_m2": new_water_area_image.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi, scale=10, maxPixels=1e9, bestEffort=True
        ).get("new_water_area"),
        "valid_area_m2": valid_area_image.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi, scale=10, maxPixels=1e9, bestEffort=True
        ).get("valid_area"),
    }).getInfo()

    before_mean_vv = final_results["before_mean_vv"]
    after_mean_vv = final_results["after_mean_vv"]
    mean_diff = final_results["mean_vv_difference"]
    otsu_threshold_value = final_results["otsu_threshold"]
    new_water_area_m2 = final_results["new_water_area_m2"] or 0
    valid_area_m2 = final_results["valid_area_m2"] or 0

    if before_mean_vv is None or after_mean_vv is None or mean_diff is None:
        raise FloodDataError(
            "Sentinel-1 backscatter statistics could not be computed for "
            "this area and period."
        )

    new_water_area_km2 = new_water_area_m2 / 1_000_000
    valid_area_km2 = valid_area_m2 / 1_000_000

    new_water_percent_of_valid_area = (
        (new_water_area_km2 / valid_area_km2 * 100) if valid_area_km2 > 0 else 0.0
    )

    warnings.append(
        "Flood evidence is based on SAR backscatter change, not a validated "
        "flood damage assessment. Results indicate likely new standing water, "
        "not flood depth, duration, or damage to structures or crops."
    )
    warnings.append(
        "Steep terrain and permanent water bodies have been excluded from "
        "this result. Dense urban areas and dense vegetation can also hide "
        "flooding from SAR and are not separately flagged here."
    )

    return {
        "method": "sentinel1_sar_otsu_threshold",
        "orbit_matched": orbit_matched,
        "before_observations": before_observations,
        "after_observations": after_observations,
        "before_mean_vv_db": before_mean_vv,
        "after_mean_vv_db": after_mean_vv,
        "mean_vv_difference_db": mean_diff,
        "otsu_threshold_db": otsu_threshold_value,
        "new_water_area_km2": new_water_area_km2,
        "valid_area_km2": valid_area_km2,
        "new_water_percent_of_valid_area": new_water_percent_of_valid_area,
        "warnings": warnings,
    }