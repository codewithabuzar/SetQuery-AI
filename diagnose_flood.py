import time

import ee

from flood_analysis import (
    _ensure_ee_initialized,
    _build_sentinel1_collection,
    _pick_shared_orbit,
    COMPOSITE_WINDOW_DAYS,
    PERMANENT_WATER_OCCURRENCE_THRESHOLD,
    SLOPE_MASK_DEGREES,
    DROP_STDDEV_MULTIPLIER,
    ABSOLUTE_WATER_VV_DB,
)

start_time = time.perf_counter()

_ensure_ee_initialized()

latitude = 26.7333
longitude = 67.6333
before_date = "2022-05-01"
after_date = "2022-08-30"
radius_km = 5

aoi = ee.Geometry.Point([longitude, latitude]).buffer(radius_km * 1000)

before_date_obj = ee.Date(before_date)
after_date_obj = ee.Date(after_date)

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

shared_orbit = _pick_shared_orbit(orbit_info["before_orbits"], orbit_info["after_orbits"])

if shared_orbit is not None:
    before_collection = before_collection.filter(ee.Filter.eq("relativeOrbitNumber_start", shared_orbit))
    after_collection = after_collection.filter(ee.Filter.eq("relativeOrbitNumber_start", shared_orbit))

speckle_kernel = ee.Kernel.square(radius=1)

before_image = before_collection.median().focal_median(kernel=speckle_kernel, iterations=1).clip(aoi)
after_image = after_collection.median().focal_median(kernel=speckle_kernel, iterations=1).clip(aoi)

gsw_occurrence = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")
permanent_water_free_mask = gsw_occurrence.gte(PERMANENT_WATER_OCCURRENCE_THRESHOLD).unmask(0).Not().rename("flood")

dem = ee.Image("USGS/SRTMGL1_003")
slope = ee.Terrain.slope(dem)
terrain_ok_mask = slope.lt(SLOPE_MASK_DEGREES).rename("flood")

difference = after_image.subtract(before_image).rename("vv_diff")

diff_stats = difference.reduceRegion(
    reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
    geometry=aoi,
    scale=10,
    maxPixels=1e9,
    bestEffort=True,
)

diff_mean = ee.Number(diff_stats.get("vv_diff_mean"))
diff_stddev = ee.Number(diff_stats.get("vv_diff_stdDev"))
adaptive_threshold = diff_mean.subtract(diff_stddev.multiply(DROP_STDDEV_MULTIPLIER))

drop_mask = difference.lt(adaptive_threshold).rename("flood")
absolute_mask = after_image.lt(ABSOLUTE_WATER_VV_DB).rename("flood")
combined_mask = drop_mask.And(absolute_mask).rename("flood")

pixel_area = ee.Image.pixelArea()


def area_km2(mask_image, name):
    masked = mask_image.multiply(pixel_area).multiply(terrain_ok_mask).multiply(permanent_water_free_mask)
    reduced = masked.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=10,
        maxPixels=1e9,
        bestEffort=True,
    )
    return reduced.get(name)


valid_area_reduced = terrain_ok_mask.multiply(pixel_area).reduceRegion(
    reducer=ee.Reducer.sum(),
    geometry=aoi,
    scale=10,
    maxPixels=1e9,
    bestEffort=True,
)
valid_area_m2 = valid_area_reduced.get("flood")

results = ee.Dictionary({
    "diff_mean": diff_mean,
    "diff_stddev": diff_stddev,
    "adaptive_threshold": adaptive_threshold,
    "drop_only_area_m2": area_km2(drop_mask, "flood"),
    "absolute_only_area_m2": area_km2(absolute_mask, "flood"),
    "combined_area_m2": area_km2(combined_mask, "flood"),
    "valid_area_m2": valid_area_m2,
}).getInfo()

elapsed = time.perf_counter() - start_time

valid_km2 = results["valid_area_m2"] / 1000000

drop_km2 = results["drop_only_area_m2"] / 1000000
absolute_km2 = results["absolute_only_area_m2"] / 1000000
combined_km2 = results["combined_area_m2"] / 1000000

print("Diff mean (dB):", round(results["diff_mean"], 4))
print("Diff stddev (dB):", round(results["diff_stddev"], 4))
print("Adaptive threshold (dB):", round(results["adaptive_threshold"], 4))
print()
print("Valid area km2:", round(valid_km2, 4))
print()
print("Drop-mask-only area km2:", round(drop_km2, 4))
print("Drop-mask-only percent:", round(drop_km2 / valid_km2 * 100, 2))
print()
print("Absolute-mask-only area km2:", round(absolute_km2, 4))
print("Absolute-mask-only percent:", round(absolute_km2 / valid_km2 * 100, 2))
print()
print("Combined area km2:", round(combined_km2, 4))
print("Combined percent:", round(combined_km2 / valid_km2 * 100, 2))
print()
print("Time:", round(elapsed, 1), "seconds")