import ee

PROJECT_ID = "optimum-reactor-510109-b5"

ee.Initialize(project=PROJECT_ID)


PROBABILITY_BANDS = [
    "water",
    "trees",
    "grass",
    "flooded_vegetation",
    "crops",
    "shrub_and_scrub",
    "built",
    "bare",
    "snow_and_ice",
]


# ==========================================================
# 1. LAND-COVER CHANGE ANALYSIS
# ==========================================================

def analyze_area(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=0.60,
):

    latitude = float(latitude)
    longitude = float(longitude)
    radius_km = float(radius_km)

    location = ee.Geometry.Point([
        longitude,
        latitude
    ])

    area = location.buffer(
        radius_km * 1000
    )

    # ------------------------------------------------------
    # Build Dynamic World probability composite
    # ------------------------------------------------------

    def build_composite(date_string):

        date = ee.Date(str(date_string))

        collection = (
            ee.ImageCollection(
                "GOOGLE/DYNAMICWORLD/V1"
            )
            .filterBounds(area)
            .filterDate(
                date.advance(-45, "day"),
                date.advance(45, "day")
            )
        )

        probabilities = (
            collection
            .select(PROBABILITY_BANDS)
            .mean()
            .clip(area)
        )

        confidence = (
            probabilities
            .reduce(ee.Reducer.max())
            .rename("confidence")
        )

        land = (
            probabilities
            .toArray()
            .arrayArgmax()
            .arrayGet([0])
            .rename("land")
        )

        return {
            "land": land,
            "confidence": confidence,
            "count": collection.size(),
        }

    # ------------------------------------------------------
    # BEFORE / AFTER
    # ------------------------------------------------------

    before = build_composite(before_date)
    after = build_composite(after_date)

    # Pixels must be high-confidence in BOTH periods.
    valid = (
        before["confidence"]
        .gte(confidence_threshold)
        .And(
            after["confidence"]
            .gte(confidence_threshold)
        )
    )

    before_land = (
        before["land"]
        .updateMask(valid)
    )

    after_land = (
        after["land"]
        .updateMask(valid)
    )

    # ------------------------------------------------------
    # Land-cover groups
    # ------------------------------------------------------

    before_vegetation = (
        before_land
        .gte(1)
        .And(before_land.lte(5))
    )

    after_vegetation = (
        after_land
        .gte(1)
        .And(after_land.lte(5))
    )

    before_water = before_land.eq(0)
    after_water = after_land.eq(0)

    before_built = before_land.eq(6)
    after_built = after_land.eq(6)

    before_bare = before_land.eq(7)
    after_bare = after_land.eq(7)

    # ------------------------------------------------------
    # Area image (km²)
    # ------------------------------------------------------

    km2 = (
        ee.Image.pixelArea()
        .divide(1e6)
    )

    # ------------------------------------------------------
    # One statistics image
    # ------------------------------------------------------

    stats_image = ee.Image.cat([

        km2
        .updateMask(valid)
        .rename("comparable"),

        km2
        .updateMask(before_vegetation)
        .rename("before_vegetation"),

        km2
        .updateMask(after_vegetation)
        .rename("after_vegetation"),

        km2
        .updateMask(before_water)
        .rename("before_water"),

        km2
        .updateMask(after_water)
        .rename("after_water"),

        km2
        .updateMask(before_built)
        .rename("before_built"),

        km2
        .updateMask(after_built)
        .rename("after_built"),

        km2
        .updateMask(before_bare)
        .rename("before_bare"),

        km2
        .updateMask(after_bare)
        .rename("after_bare"),

        km2
        .updateMask(
            before_vegetation
            .And(after_built)
        )
        .rename("vegetation_to_built"),

        km2
        .updateMask(
            before_built
            .And(after_vegetation)
        )
        .rename("built_to_vegetation"),

        km2
        .updateMask(
            before_bare
            .And(after_built)
        )
        .rename("bare_to_built"),

        km2
        .updateMask(
            before_water
            .And(after_land.neq(0))
        )
        .rename("water_to_nonwater"),

        km2
        .updateMask(
            before_land
            .neq(0)
            .And(after_water)
        )
        .rename("nonwater_to_water"),
    ])

    # ------------------------------------------------------
    # One reduction
    # ------------------------------------------------------

    stats = stats_image.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=area,
        scale=10,
        maxPixels=1e9,
        tileScale=4,
    )

    total_area = (
        area.area()
        .divide(1e6)
    )

    comparable_area = ee.Number(
        stats.get("comparable")
    )

    coverage = (
        comparable_area
        .divide(total_area)
        .multiply(100)
    )

    # ------------------------------------------------------
    # Structured result
    # ------------------------------------------------------

    result = ee.Dictionary({

        "before_observations":
            before["count"],

        "after_observations":
            after["count"],

        "total_area_km2":
            total_area,

        "comparable_area_km2":
            comparable_area,

        "coverage_percent":
            coverage,

        "before_vegetation_km2":
            stats.get("before_vegetation"),

        "after_vegetation_km2":
            stats.get("after_vegetation"),

        "before_built_km2":
            stats.get("before_built"),

        "after_built_km2":
            stats.get("after_built"),

        "before_water_km2":
            stats.get("before_water"),

        "after_water_km2":
            stats.get("after_water"),

        "before_bare_km2":
            stats.get("before_bare"),

        "after_bare_km2":
            stats.get("after_bare"),

        "vegetation_to_built_km2":
            stats.get("vegetation_to_built"),

        "built_to_vegetation_km2":
            stats.get("built_to_vegetation"),

        "bare_to_built_km2":
            stats.get("bare_to_built"),

        "water_to_nonwater_km2":
            stats.get("water_to_nonwater"),

        "nonwater_to_water_km2":
            stats.get("nonwater_to_water"),
    })

    return result.getInfo()


# ==========================================================
# 2. SENTINEL-2 BEFORE / AFTER IMAGERY
# ==========================================================

def get_satellite_images(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
):

    latitude = float(latitude)
    longitude = float(longitude)
    radius_km = float(radius_km)

    location = ee.Geometry.Point([
        longitude,
        latitude
    ])

    area = location.buffer(
        radius_km * 1000
    )

    # ------------------------------------------------------
    # Pixel-level cloud masking
    # ------------------------------------------------------

    def mask_clouds(image):

        scl = image.select("SCL")

        mask = (
            scl.neq(3)
            .And(scl.neq(8))
            .And(scl.neq(9))
            .And(scl.neq(10))
            .And(scl.neq(11))
        )

        return image.updateMask(mask)

    # ------------------------------------------------------
    # Build Sentinel-2 composite
    # ------------------------------------------------------

    def build_image(date_string):

        target = ee.Date(
            str(date_string)
        )

        start = target.advance(
            -45,
            "day"
        )

        end = target.advance(
            45,
            "day"
        )

        collection = (
            ee.ImageCollection(
                "COPERNICUS/S2_SR_HARMONIZED"
            )
            .filterBounds(area)
            .filterDate(start, end)
            .filter(
                ee.Filter.lt(
                    "CLOUDY_PIXEL_PERCENTAGE",
                    90
                )
            )
            .map(mask_clouds)
        )

        image = (
            collection
            .median()
            .clip(area)
        )

        return (
            image,
            collection.size()
        )

    # ------------------------------------------------------
    # BEFORE / AFTER
    # ------------------------------------------------------

    before_image, before_count = (
        build_image(before_date)
    )

    after_image, after_count = (
        build_image(after_date)
    )

    # ------------------------------------------------------
    # Natural RGB
    # ------------------------------------------------------

    rgb_vis = {
        "bands": [
            "B4",
            "B3",
            "B2"
        ],
        "min": 0,
        "max": 3000,
        "gamma": 1.1,
    }

    before_rgb = (
        before_image
        .visualize(**rgb_vis)
    )

    after_rgb = (
        after_image
        .visualize(**rgb_vis)
    )

    # ------------------------------------------------------
    # Thumbnail URLs
    # ------------------------------------------------------

    thumbnail_params = {
        "region": area,
        "dimensions": 700,
        "format": "png",
    }

    before_url = (
        before_rgb
        .getThumbURL(thumbnail_params)
    )

    after_url = (
        after_rgb
        .getThumbURL(thumbnail_params)
    )

    return {
        "before_url":
            before_url,

        "after_url":
            after_url,

        "before_sentinel_observations":
            before_count.getInfo(),

        "after_sentinel_observations":
            after_count.getInfo(),
    }