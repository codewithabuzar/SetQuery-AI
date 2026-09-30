from datetime import date, datetime, timedelta

import ee


PROJECT_ID = "optimum-reactor-510109-b5"

ee.Initialize(project=PROJECT_ID)


# ==========================================================
# CONFIGURATION
# ==========================================================

COMPOSITE_WINDOW_DAYS = 45

MIN_RADIUS_KM = 1
MAX_RADIUS_KM = 20

# Landsat Collection 2 Level-2 collections.
#
# Priority is intentional:
# newer sensors are preferred where they are available.
LANDSAT_COLLECTIONS = (
    {
        "id": "LANDSAT/LC09/C02/T1_L2",
        "name": "Landsat 9",
        "sensor": "OLI-2",
        "red": "SR_B4",
        "green": "SR_B3",
        "blue": "SR_B2",
        "nir": "SR_B5",
        "swir1": "SR_B6",
    },
    {
        "id": "LANDSAT/LC08/C02/T1_L2",
        "name": "Landsat 8",
        "sensor": "OLI",
        "red": "SR_B4",
        "green": "SR_B3",
        "blue": "SR_B2",
        "nir": "SR_B5",
        "swir1": "SR_B6",
    },
    {
        "id": "LANDSAT/LE07/C02/T1_L2",
        "name": "Landsat 7",
        "sensor": "ETM+",
        "red": "SR_B3",
        "green": "SR_B2",
        "blue": "SR_B1",
        "nir": "SR_B4",
        "swir1": "SR_B5",
    },
    {
        "id": "LANDSAT/LT05/C02/T1_L2",
        "name": "Landsat 5",
        "sensor": "TM",
        "red": "SR_B3",
        "green": "SR_B2",
        "blue": "SR_B1",
        "nir": "SR_B4",
        "swir1": "SR_B5",
    },
)


# ==========================================================
# ERRORS
# ==========================================================

class HistoricalValidationError(ValueError):
    """Invalid historical-analysis request."""


class HistoricalDataError(RuntimeError):
    """Required historical satellite data is unavailable."""


# ==========================================================
# VALIDATION
# ==========================================================

def _parse_date(value, field_name):
    """
    Normalize date input.
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
        raise HistoricalValidationError(
            f"{field_name} must use YYYY-MM-DD format."
        ) from error


def _validate_coordinates(
    latitude,
    longitude,
):
    """
    Validate geographic coordinates.
    """

    try:
        latitude = float(latitude)
        longitude = float(longitude)

    except (TypeError, ValueError) as error:
        raise HistoricalValidationError(
            "Latitude and longitude must be numeric."
        ) from error

    if not -90 <= latitude <= 90:
        raise HistoricalValidationError(
            "Latitude must be between -90 and 90."
        )

    if not -180 <= longitude <= 180:
        raise HistoricalValidationError(
            "Longitude must be between -180 and 180."
        )

    return latitude, longitude


def _validate_radius(radius_km):
    """
    Validate application radius.
    """

    try:
        radius_km = float(radius_km)

    except (TypeError, ValueError) as error:
        raise HistoricalValidationError(
            "Radius must be numeric."
        ) from error

    if not MIN_RADIUS_KM <= radius_km <= MAX_RADIUS_KM:
        raise HistoricalValidationError(
            f"Radius must be between "
            f"{MIN_RADIUS_KM} and "
            f"{MAX_RADIUS_KM} km."
        )

    return radius_km


def validate_historical_request(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
):
    """
    Validate a historical imagery request.
    """

    latitude, longitude = (
        _validate_coordinates(
            latitude,
            longitude,
        )
    )

    radius_km = _validate_radius(
        radius_km
    )

    before = _parse_date(
        before_date,
        "Before date",
    )

    after = _parse_date(
        after_date,
        "After date",
    )

    if before >= after:
        raise HistoricalValidationError(
            "Before date must be earlier than after date."
        )

    today = date.today()

    if before > today or after > today:
        raise HistoricalValidationError(
            "Historical analysis dates cannot be "
            "in the future."
        )

    return {
        "latitude": latitude,
        "longitude": longitude,
        "radius_km": radius_km,
        "before_date": before,
        "after_date": after,
    }


# ==========================================================
# GEOMETRY / WINDOWS
# ==========================================================

def _create_area(
    latitude,
    longitude,
    radius_km,
):
    """
    Create Earth Engine analysis geometry.
    """

    point = ee.Geometry.Point(
        [
            longitude,
            latitude,
        ]
    )

    return point.buffer(
        radius_km * 1000
    )


def _date_window(target):
    """
    Create approximately ±45-day search window.
    """

    start = (
        target
        - timedelta(
            days=COMPOSITE_WINDOW_DAYS
        )
    )

    end_exclusive = (
        target
        + timedelta(
            days=COMPOSITE_WINDOW_DAYS
        )
    )

    return {
        "target_date":
            target.isoformat(),

        "start":
            start.isoformat(),

        "end_exclusive":
            end_exclusive.isoformat(),
    }


# ==========================================================
# LANDSAT PREPROCESSING
# ==========================================================

def _mask_landsat(image):
    """
    Mask common Landsat Collection 2 QA conditions.

    QA_PIXEL bits:
    bit 0 = fill
    bit 1 = dilated cloud
    bit 2 = cirrus
    bit 3 = cloud
    bit 4 = cloud shadow
    bit 5 = snow

    QA_RADSAT == 0 excludes radiometrically saturated pixels.
    """

    qa = image.select(
        "QA_PIXEL"
    )

    fill = (
        qa.bitwiseAnd(1 << 0)
        .eq(0)
    )

    dilated_cloud = (
        qa.bitwiseAnd(1 << 1)
        .eq(0)
    )

    cirrus = (
        qa.bitwiseAnd(1 << 2)
        .eq(0)
    )

    cloud = (
        qa.bitwiseAnd(1 << 3)
        .eq(0)
    )

    cloud_shadow = (
        qa.bitwiseAnd(1 << 4)
        .eq(0)
    )

    snow = (
        qa.bitwiseAnd(1 << 5)
        .eq(0)
    )

    saturation = (
        image
        .select("QA_RADSAT")
        .eq(0)
    )

    mask = (
        fill
        .And(dilated_cloud)
        .And(cirrus)
        .And(cloud)
        .And(cloud_shadow)
        .And(snow)
        .And(saturation)
    )

    return image.updateMask(
        mask
    )


def _apply_scale_factors(image):
    """
    Convert Landsat Collection 2 optical SR bands
    to scaled surface reflectance.

    USGS scale:
        reflectance = DN * 0.0000275 - 0.2
    """

    optical = (
        image
        .select("SR_B.")
        .multiply(0.0000275)
        .add(-0.2)
    )

    return (
        image
        .addBands(
            optical,
            None,
            True,
        )
    )


def _build_collection(
    sensor,
    area,
    window,
):
    """
    Build one sensor-specific Landsat collection.
    """

    return (
        ee.ImageCollection(
            sensor["id"]
        )
        .filterBounds(area)
        .filterDate(
            window["start"],
            window["end_exclusive"],
        )
        .map(_mask_landsat)
        .map(_apply_scale_factors)
    )


def _collection_count(collection):
    """
    Get a Landsat collection count.
    """

    try:
        return int(
            collection
            .size()
            .getInfo()
        )

    except Exception as error:
        raise HistoricalDataError(
            "Earth Engine could not check historical "
            "Landsat availability."
        ) from error


# ==========================================================
# SENSOR DISCOVERY
# ==========================================================

def find_available_sensors(
    area,
    window,
):
    """
    Dynamically discover Landsat sensors with observations
    intersecting the requested location/window.

    This is location-aware; it is not city-specific.
    """

    available = []

    for sensor in LANDSAT_COLLECTIONS:

        collection = (
            _build_collection(
                sensor=sensor,
                area=area,
                window=window,
            )
        )

        count = _collection_count(
            collection
        )

        if count > 0:
            available.append(
                {
                    "sensor": sensor,
                    "collection": collection,
                    "count": count,
                }
            )

    return available


# ==========================================================
# COMPOSITE
# ==========================================================

def _build_composite(
    available_sensors,
    area,
):
    """
    Build a harmonized visual composite.

    Multiple available Landsat missions can contribute.
    Their corresponding visible bands are renamed to a
    common RED/GREEN/BLUE schema before merging.
    """

    normalized_collections = []

    sensor_metadata = []

    for item in available_sensors:

        sensor = item[
            "sensor"
        ]

        collection = item[
            "collection"
        ]

        normalized = (
            collection.map(
                lambda image: (
                    image.select(
                        [
                            sensor["red"],
                            sensor["green"],
                            sensor["blue"],
                        ],
                        [
                            "red",
                            "green",
                            "blue",
                        ],
                    )
                )
            )
        )

        normalized_collections.append(
            normalized
        )

        sensor_metadata.append(
            {
                "name":
                    sensor["name"],

                "sensor":
                    sensor["sensor"],

                "observations":
                    item["count"],
            }
        )

    merged = (
        normalized_collections[0]
    )

    for collection in (
        normalized_collections[1:]
    ):
        merged = merged.merge(
            collection
        )

    composite = (
        merged
        .median()
        .clip(area)
    )

    return (
        composite,
        sensor_metadata,
    )


# ==========================================================
# PUBLIC HISTORICAL IMAGERY FUNCTION
# ==========================================================

def get_historical_satellite_images(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
):
    """
    Build historical BEFORE and AFTER Landsat imagery.

    This stage provides imagery and availability metadata.
    It does NOT yet claim historical land-cover
    classification/change statistics.
    """

    request = (
        validate_historical_request(
            latitude=latitude,
            longitude=longitude,
            before_date=before_date,
            after_date=after_date,
            radius_km=radius_km,
        )
    )

    area = _create_area(
        request["latitude"],
        request["longitude"],
        request["radius_km"],
    )

    before_window = _date_window(
        request["before_date"]
    )

    after_window = _date_window(
        request["after_date"]
    )

    before_sensors = (
        find_available_sensors(
            area,
            before_window,
        )
    )

    after_sensors = (
        find_available_sensors(
            area,
            after_window,
        )
    )

    if not before_sensors:
        raise HistoricalDataError(
            "No supported Landsat observations were found "
            "for the BEFORE composite window."
        )

    if not after_sensors:
        raise HistoricalDataError(
            "No supported Landsat observations were found "
            "for the AFTER composite window."
        )

    (
        before_composite,
        before_sensor_metadata,
    ) = _build_composite(
        before_sensors,
        area,
    )

    (
        after_composite,
        after_sensor_metadata,
    ) = _build_composite(
        after_sensors,
        area,
    )

    visualization = {
        "bands": [
            "red",
            "green",
            "blue",
        ],

        # Landsat SR has already been scaled.
        "min": 0.0,
        "max": 0.30,
        "gamma": 1.1,
    }

    before_rgb = (
        before_composite
        .visualize(
            **visualization
        )
    )

    after_rgb = (
        after_composite
        .visualize(
            **visualization
        )
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
        raise HistoricalDataError(
            "Earth Engine could not generate the "
            "historical Landsat preview."
        ) from error

    before_total = sum(
        item["observations"]
        for item in before_sensor_metadata
    )

    after_total = sum(
        item["observations"]
        for item in after_sensor_metadata
    )

    warnings = []

    if any(
        item["name"] == "Landsat 7"
        for item in before_sensor_metadata
    ):
        warnings.append(
            "The BEFORE composite includes Landsat 7. "
            "Landsat 7 scenes after 2003 can contain "
            "scan-line gaps; multi-scene compositing helps "
            "reduce but may not eliminate their effect."
        )

    if any(
        item["name"] == "Landsat 7"
        for item in after_sensor_metadata
    ):
        warnings.append(
            "The AFTER composite includes Landsat 7. "
            "Post-2003 Landsat 7 scan-line gaps may affect "
            "spatial completeness."
        )

    return {
        "analysis_mode":
            "historical_landsat",

        "spatial_resolution_note":
            "Landsat optical imagery is approximately "
            "30 m for the bands used in this workflow.",

        "before_url":
            before_url,

        "after_url":
            after_url,

        "before_observations":
            before_total,

        "after_observations":
            after_total,

        "before_sensors":
            before_sensor_metadata,

        "after_sensors":
            after_sensor_metadata,

        "before_window":
            before_window,

        "after_window":
            after_window,

        "warnings":
            warnings,
    }