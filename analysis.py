from datetime import date, datetime, timedelta

import ee


# ==========================================================
# CONFIGURATION
# ==========================================================

PROJECT_ID = "optimum-reactor-510109-b5"

DYNAMIC_WORLD_COLLECTION = "GOOGLE/DYNAMICWORLD/V1"
SENTINEL_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"

COMPOSITE_WINDOW_DAYS = 45
MIN_DATE_SEPARATION_DAYS = 90

MIN_RADIUS_KM = 1
MAX_RADIUS_KM = 20

DEFAULT_CONFIDENCE_THRESHOLD = 0.60

# This does not make a scientific claim about data quality.
# It is simply used to warn that a composite has relatively
# few source observations.
LOW_OBSERVATION_WARNING_COUNT = 3

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
# EARTH ENGINE INITIALIZATION
# ==========================================================

ee.Initialize(project=PROJECT_ID)


# ==========================================================
# CUSTOM ERRORS
# ==========================================================

class AnalysisValidationError(ValueError):
    """Raised when an analysis request is invalid."""


class AnalysisDataError(RuntimeError):
    """Raised when required Earth Engine data is unavailable."""


# ==========================================================
# VALIDATION / METADATA HELPERS
# ==========================================================

def _parse_date(value, field_name):
    """
    Convert a date/date-string into a Python date.
    """

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    try:
        return datetime.strptime(
            str(value),
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError) as error:
        raise AnalysisValidationError(
            f"{field_name} must use YYYY-MM-DD format."
        ) from error


def _validate_coordinates(latitude, longitude):
    """
    Validate latitude and longitude values.
    """

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError) as error:
        raise AnalysisValidationError(
            "Latitude and longitude must be numeric."
        ) from error

    if not -90 <= latitude <= 90:
        raise AnalysisValidationError(
            "Latitude must be between -90 and 90 degrees."
        )

    if not -180 <= longitude <= 180:
        raise AnalysisValidationError(
            "Longitude must be between -180 and 180 degrees."
        )

    return latitude, longitude


def _validate_radius(radius_km):
    """
    Validate the application analysis radius.
    """

    try:
        radius_km = float(radius_km)
    except (TypeError, ValueError) as error:
        raise AnalysisValidationError(
            "Analysis radius must be numeric."
        ) from error

    if radius_km < MIN_RADIUS_KM:
        raise AnalysisValidationError(
            f"Analysis radius must be at least "
            f"{MIN_RADIUS_KM} km."
        )

    if radius_km > MAX_RADIUS_KM:
        raise AnalysisValidationError(
            f"Analysis radius cannot exceed "
            f"{MAX_RADIUS_KM} km."
        )

    return radius_km


def _validate_confidence_threshold(confidence_threshold):
    """
    Validate Dynamic World confidence threshold.
    """

    try:
        confidence_threshold = float(
            confidence_threshold
        )
    except (TypeError, ValueError) as error:
        raise AnalysisValidationError(
            "Confidence threshold must be numeric."
        ) from error

    if not 0 < confidence_threshold <= 1:
        raise AnalysisValidationError(
            "Confidence threshold must be greater "
            "than 0 and no greater than 1."
        )

    return confidence_threshold


def _build_window_metadata(target_date):
    """
    Build requested and effective composite-window metadata.

    Earth Engine filterDate uses:
        start inclusive
        end exclusive

    If the requested window extends beyond today, the
    effective end is truncated to tomorrow so today's
    available imagery can still be included.
    """

    today = date.today()

    requested_start = (
        target_date
        - timedelta(days=COMPOSITE_WINDOW_DAYS)
    )

    requested_end_exclusive = (
        target_date
        + timedelta(days=COMPOSITE_WINDOW_DAYS)
    )

    tomorrow = today + timedelta(days=1)

    effective_start = requested_start
    effective_end_exclusive = min(
        requested_end_exclusive,
        tomorrow,
    )

    truncated = (
        effective_end_exclusive
        < requested_end_exclusive
    )

    return {
        "target_date":
            target_date.isoformat(),

        "requested_start":
            requested_start.isoformat(),

        "requested_end_exclusive":
            requested_end_exclusive.isoformat(),

        "effective_start":
            effective_start.isoformat(),

        "effective_end_exclusive":
            effective_end_exclusive.isoformat(),

        "future_truncated":
            truncated,
    }


def validate_analysis_request(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """
    Validate an analysis request before Earth Engine work.

    Returns normalized values and composite metadata.
    """

    latitude, longitude = _validate_coordinates(
        latitude,
        longitude,
    )

    radius_km = _validate_radius(
        radius_km
    )

    confidence_threshold = (
        _validate_confidence_threshold(
            confidence_threshold
        )
    )

    before = _parse_date(
        before_date,
        "Before date",
    )

    after = _parse_date(
        after_date,
        "After date",
    )

    today = date.today()

    if before >= after:
        raise AnalysisValidationError(
            "Before date must be earlier than after date."
        )

    if before > today:
        raise AnalysisValidationError(
            "Before date cannot be in the future."
        )

    if after > today:
        raise AnalysisValidationError(
            "After date cannot be in the future."
        )

    separation_days = (
        after - before
    ).days

    if separation_days < MIN_DATE_SEPARATION_DAYS:
        raise AnalysisValidationError(
            "Before and after target dates must be at "
            f"least {MIN_DATE_SEPARATION_DAYS} days apart. "
            "This reduces overlap between the approximately "
            f"±{COMPOSITE_WINDOW_DAYS}-day composite windows."
        )

    before_window = _build_window_metadata(
        before
    )

    after_window = _build_window_metadata(
        after
    )

    warnings = []

    if before_window["future_truncated"]:
        warnings.append(
            "The BEFORE composite window extends beyond "
            "today and was truncated to currently available "
            "dates."
        )

    if after_window["future_truncated"]:
        warnings.append(
            "The AFTER composite window extends beyond "
            "today and was truncated to currently available "
            "dates."
        )

    return {
        "latitude":
            latitude,

        "longitude":
            longitude,

        "radius_km":
            radius_km,

        "confidence_threshold":
            confidence_threshold,

        "before_date":
            before.isoformat(),

        "after_date":
            after.isoformat(),

        "date_separation_days":
            separation_days,

        "before_window":
            before_window,

        "after_window":
            after_window,

        "warnings":
            warnings,
    }


def _create_area(latitude, longitude, radius_km):
    """
    Create the Earth Engine study geometry.
    """

    location = ee.Geometry.Point([
        longitude,
        latitude,
    ])

    return location.buffer(
        radius_km * 1000
    )


def _get_collection_count(collection, label):
    """
    Retrieve and validate collection observation count.
    """

    try:
        count = int(
            collection.size().getInfo()
        )
    except Exception as error:
        raise AnalysisDataError(
            f"Could not check {label} observations. "
            "Earth Engine or the network may be temporarily "
            "unavailable."
        ) from error

    return count


def _observation_warnings(
    before_count,
    after_count,
    dataset_name,
):
    """
    Build conservative warnings for small collections.
    """

    warnings = []

    if (
        before_count
        < LOW_OBSERVATION_WARNING_COUNT
    ):
        warnings.append(
            f"Only {before_count} {dataset_name} "
            "observation(s) were available for the "
            "BEFORE composite."
        )

    if (
        after_count
        < LOW_OBSERVATION_WARNING_COUNT
    ):
        warnings.append(
            f"Only {after_count} {dataset_name} "
            "observation(s) were available for the "
            "AFTER composite."
        )

    return warnings


def _build_dynamic_world_composite(
    area,
    window,
):
    """
    Build a Dynamic World probability composite.
    """

    collection = (
        ee.ImageCollection(
            DYNAMIC_WORLD_COLLECTION
        )
        .filterBounds(area)
        .filterDate(
            window["effective_start"],
            window["effective_end_exclusive"],
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
        "collection":
            collection,

        "probabilities":
            probabilities,

        "confidence":
            confidence,

        "land":
            land,
    }


def _mask_sentinel_clouds(image):
    """
    Mask selected Sentinel-2 SCL cloud/snow classes.
    """

    scl = image.select("SCL")

    mask = (
        scl.neq(3)
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )

    return image.updateMask(mask)


def _build_sentinel_collection(
    area,
    window,
):
    """
    Build the filtered Sentinel-2 collection.
    """

    return (
        ee.ImageCollection(
            SENTINEL_COLLECTION
        )
        .filterBounds(area)
        .filterDate(
            window["effective_start"],
            window["effective_end_exclusive"],
        )
        .filter(
            ee.Filter.lt(
                "CLOUDY_PIXEL_PERCENTAGE",
                90,
            )
        )
        .map(_mask_sentinel_clouds)
    )


# ==========================================================
# 1. LAND-COVER CHANGE ANALYSIS
# ==========================================================

def analyze_area(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):

    request = validate_analysis_request(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=confidence_threshold,
    )

    area = _create_area(
        request["latitude"],
        request["longitude"],
        request["radius_km"],
    )

    before = _build_dynamic_world_composite(
        area,
        request["before_window"],
    )

    after = _build_dynamic_world_composite(
        area,
        request["after_window"],
    )

    before_count = _get_collection_count(
        before["collection"],
        "Dynamic World BEFORE",
    )

    after_count = _get_collection_count(
        after["collection"],
        "Dynamic World AFTER",
    )

    if before_count == 0:
        raise AnalysisDataError(
            "No Dynamic World observations were found "
            "for the BEFORE composite window."
        )

    if after_count == 0:
        raise AnalysisDataError(
            "No Dynamic World observations were found "
            "for the AFTER composite window."
        )

    warnings = list(
        request["warnings"]
    )

    warnings.extend(
        _observation_warnings(
            before_count,
            after_count,
            "Dynamic World",
        )
    )

    valid = (
        before["confidence"]
        .gte(
            request[
                "confidence_threshold"
            ]
        )
        .And(
            after["confidence"]
            .gte(
                request[
                    "confidence_threshold"
                ]
            )
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
    # Statistics image
    # ------------------------------------------------------

    km2 = (
        ee.Image.pixelArea()
        .divide(1e6)
    )

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

    try:
        stats = (
            stats_image
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=area,
                scale=10,
                maxPixels=1e9,
                tileScale=4,
            )
            .getInfo()
        )

        total_area_km2 = float(
            area.area()
            .divide(1e6)
            .getInfo()
        )

    except Exception as error:
        raise AnalysisDataError(
            "Earth Engine could not calculate the "
            "land-cover statistics. Please try again."
        ) from error

    def stat_value(name):
        value = stats.get(name)

        if value is None:
            return 0.0

        return float(value)

    comparable_area_km2 = stat_value(
        "comparable"
    )

    if total_area_km2 > 0:
        coverage_percent = (
            comparable_area_km2
            / total_area_km2
            * 100
        )
    else:
        coverage_percent = 0.0

    if coverage_percent < 20:
        warnings.append(
            "Comparable coverage is very low and is "
            "insufficient for broad area-level conclusions."
        )

    elif coverage_percent < 40:
        warnings.append(
            "Comparable coverage is limited. Area-wide "
            "conclusions should be made cautiously."
        )

    result = {
        "before_observations":
            before_count,

        "after_observations":
            after_count,

        "total_area_km2":
            total_area_km2,

        "comparable_area_km2":
            comparable_area_km2,

        "coverage_percent":
            coverage_percent,

        "before_vegetation_km2":
            stat_value("before_vegetation"),

        "after_vegetation_km2":
            stat_value("after_vegetation"),

        "before_built_km2":
            stat_value("before_built"),

        "after_built_km2":
            stat_value("after_built"),

        "before_water_km2":
            stat_value("before_water"),

        "after_water_km2":
            stat_value("after_water"),

        "before_bare_km2":
            stat_value("before_bare"),

        "after_bare_km2":
            stat_value("after_bare"),

        "vegetation_to_built_km2":
            stat_value("vegetation_to_built"),

        "built_to_vegetation_km2":
            stat_value("built_to_vegetation"),

        "bare_to_built_km2":
            stat_value("bare_to_built"),

        "water_to_nonwater_km2":
            stat_value("water_to_nonwater"),

        "nonwater_to_water_km2":
            stat_value("nonwater_to_water"),

        # New metadata. Existing result keys remain unchanged.
        "confidence_threshold":
            request["confidence_threshold"],

        "date_separation_days":
            request["date_separation_days"],

        "before_window":
            request["before_window"],

        "after_window":
            request["after_window"],

        "warnings":
            warnings,
    }

    return result


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

    request = validate_analysis_request(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
    )

    area = _create_area(
        request["latitude"],
        request["longitude"],
        request["radius_km"],
    )

    before_collection = (
        _build_sentinel_collection(
            area,
            request["before_window"],
        )
    )

    after_collection = (
        _build_sentinel_collection(
            area,
            request["after_window"],
        )
    )

    before_count = _get_collection_count(
        before_collection,
        "Sentinel-2 BEFORE",
    )

    after_count = _get_collection_count(
        after_collection,
        "Sentinel-2 AFTER",
    )

    if before_count == 0:
        raise AnalysisDataError(
            "No usable Sentinel-2 observations were found "
            "for the BEFORE composite window."
        )

    if after_count == 0:
        raise AnalysisDataError(
            "No usable Sentinel-2 observations were found "
            "for the AFTER composite window."
        )

    warnings = list(
        request["warnings"]
    )

    warnings.extend(
        _observation_warnings(
            before_count,
            after_count,
            "Sentinel-2",
        )
    )

    before_image = (
        before_collection
        .median()
        .clip(area)
    )

    after_image = (
        after_collection
        .median()
        .clip(area)
    )

    rgb_vis = {
        "bands": [
            "B4",
            "B3",
            "B2",
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

    thumbnail_params = {
        "region": area,
        "dimensions": 700,
        "format": "png",
    }

    try:
        before_url = (
            before_rgb
            .getThumbURL(
                thumbnail_params
            )
        )

        after_url = (
            after_rgb
            .getThumbURL(
                thumbnail_params
            )
        )

    except Exception as error:
        raise AnalysisDataError(
            "Earth Engine could not generate the "
            "Sentinel-2 preview images."
        ) from error

    return {
        "before_url":
            before_url,

        "after_url":
            after_url,

        "before_sentinel_observations":
            before_count,

        "after_sentinel_observations":
            after_count,

        "before_window":
            request["before_window"],

        "after_window":
            request["after_window"],

        "warnings":
            warnings,
    }


# ==========================================================
# 3. HIGH-CONFIDENCE CHANGE MAP
# ==========================================================

def get_change_map(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):

    request = validate_analysis_request(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=confidence_threshold,
    )

    area = _create_area(
        request["latitude"],
        request["longitude"],
        request["radius_km"],
    )

    before = _build_dynamic_world_composite(
        area,
        request["before_window"],
    )

    after = _build_dynamic_world_composite(
        area,
        request["after_window"],
    )

    before_count = _get_collection_count(
        before["collection"],
        "Dynamic World BEFORE change-map",
    )

    after_count = _get_collection_count(
        after["collection"],
        "Dynamic World AFTER change-map",
    )

    if before_count == 0:
        raise AnalysisDataError(
            "No Dynamic World observations were found "
            "for the BEFORE change-map window."
        )

    if after_count == 0:
        raise AnalysisDataError(
            "No Dynamic World observations were found "
            "for the AFTER change-map window."
        )

    valid = (
        before["confidence"]
        .gte(
            request[
                "confidence_threshold"
            ]
        )
        .And(
            after["confidence"]
            .gte(
                request[
                    "confidence_threshold"
                ]
            )
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

    before_veg = (
        before_land
        .gte(1)
        .And(before_land.lte(5))
    )

    after_veg = (
        after_land
        .gte(1)
        .And(after_land.lte(5))
    )

    before_built = before_land.eq(6)
    after_built = after_land.eq(6)

    before_bare = before_land.eq(7)

    before_water = before_land.eq(0)
    after_water = after_land.eq(0)

    vegetation_to_built = (
        before_veg
        .And(after_built)
    )

    built_to_vegetation = (
        before_built
        .And(after_veg)
    )

    bare_to_built = (
        before_bare
        .And(after_built)
    )

    nonwater_to_water = (
        before_land
        .neq(0)
        .And(after_water)
    )

    water_to_nonwater = (
        before_water
        .And(after_land.neq(0))
    )

    change = (
        ee.Image(0)
        .where(
            vegetation_to_built,
            1,
        )
        .where(
            built_to_vegetation,
            2,
        )
        .where(
            bare_to_built,
            3,
        )
        .where(
            nonwater_to_water,
            4,
        )
        .where(
            water_to_nonwater,
            5,
        )
        .clip(area)
    )

    # Visualization only. Numerical statistics continue
    # using the original, non-enlarged pixels in analyze_area.
    display_radius = 2

    veg_to_built_display = (
        change.eq(1)
        .focal_max(
            radius=display_radius,
            units="pixels",
        )
    )

    built_to_veg_display = (
        change.eq(2)
        .focal_max(
            radius=display_radius,
            units="pixels",
        )
    )

    bare_to_built_display = (
        change.eq(3)
        .focal_max(
            radius=display_radius,
            units="pixels",
        )
    )

    new_water_display = (
        change.eq(4)
        .focal_max(
            radius=display_radius,
            units="pixels",
        )
    )

    lost_water_display = (
        change.eq(5)
        .focal_max(
            radius=display_radius,
            units="pixels",
        )
    )

    display_change = (
        ee.Image(0)
        .where(
            veg_to_built_display,
            1,
        )
        .where(
            built_to_veg_display,
            2,
        )
        .where(
            bare_to_built_display,
            3,
        )
        .where(
            new_water_display,
            4,
        )
        .where(
            lost_water_display,
            5,
        )
    )

    display_change = (
        display_change
        .updateMask(
            display_change.gt(0)
        )
        .clip(area)
    )

    sentinel_collection = (
        _build_sentinel_collection(
            area,
            request["after_window"],
        )
    )

    sentinel_count = _get_collection_count(
        sentinel_collection,
        "Sentinel-2 AFTER change-map background",
    )

    if sentinel_count == 0:
        raise AnalysisDataError(
            "No usable Sentinel-2 observations were found "
            "for the change-map background."
        )

    background = (
        sentinel_collection
        .median()
        .clip(area)
        .visualize(
            bands=[
                "B4",
                "B3",
                "B2",
            ],
            min=0,
            max=3500,
            gamma=1.2,
        )
        .multiply(0.45)
        .toUint8()
    )

    colored_changes = (
        display_change
        .visualize(
            min=1,
            max=5,
            palette=[
                "FF0000",
                "00FF00",
                "FFFF00",
                "0066FF",
                "FF8800",
            ],
        )
    )

    final_map = (
        background
        .blend(colored_changes)
        .clip(area)
    )

    thumbnail_params = {
        "region": area,
        "dimensions": 800,
        "format": "png",
    }

    try:
        change_url = (
            final_map
            .getThumbURL(
                thumbnail_params
            )
        )

    except Exception as error:
        raise AnalysisDataError(
            "Earth Engine could not generate the "
            "change-map preview."
        ) from error

    warnings = list(
        request["warnings"]
    )

    warnings.extend(
        _observation_warnings(
            before_count,
            after_count,
            "Dynamic World",
        )
    )

    return {
        "change_url":
            change_url,

        "before_change_observations":
            before_count,

        "after_change_observations":
            after_count,

        "background_sentinel_observations":
            sentinel_count,

        "before_window":
            request["before_window"],

        "after_window":
            request["after_window"],

        "warnings":
            warnings,
    }