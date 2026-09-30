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

LANDSAT_COLLECTIONS = (
    {
        "id": "LANDSAT/LC09/C02/T1_L2",
        "name": "Landsat 9",
        "sensor": "OLI-2",
        "blue": "SR_B2",
        "green": "SR_B3",
        "red": "SR_B4",
        "nir": "SR_B5",
        "swir1": "SR_B6",
    },
    {
        "id": "LANDSAT/LC08/C02/T1_L2",
        "name": "Landsat 8",
        "sensor": "OLI",
        "blue": "SR_B2",
        "green": "SR_B3",
        "red": "SR_B4",
        "nir": "SR_B5",
        "swir1": "SR_B6",
    },
    {
        "id": "LANDSAT/LE07/C02/T1_L2",
        "name": "Landsat 7",
        "sensor": "ETM+",
        "blue": "SR_B1",
        "green": "SR_B2",
        "red": "SR_B3",
        "nir": "SR_B4",
        "swir1": "SR_B5",
    },
    {
        "id": "LANDSAT/LT05/C02/T1_L2",
        "name": "Landsat 5",
        "sensor": "TM",
        "blue": "SR_B1",
        "green": "SR_B2",
        "red": "SR_B3",
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
    """Historical satellite data could not be analyzed."""


# ==========================================================
# VALIDATION
# ==========================================================

def _parse_date(value, field_name):

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

    latitude, longitude = (
        _validate_coordinates(
            latitude,
            longitude,
        )
    )

    radius_km = (
        _validate_radius(
            radius_km
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

    if before >= after:
        raise HistoricalValidationError(
            "Before date must be earlier than after date."
        )

    today = date.today()

    if before > today or after > today:
        raise HistoricalValidationError(
            "Analysis dates cannot be in the future."
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
    Mask Collection 2 Level-2 fill/cloud/shadow/snow
    and radiometrically saturated pixels.
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

    optical = (
        image
        .select("SR_B.")
        .multiply(0.0000275)
        .add(-0.2)
    )

    return image.addBands(
        optical,
        None,
        True,
    )


def _build_collection(
    sensor,
    area,
    window,
):

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

    try:
        return int(
            collection
            .size()
            .getInfo()
        )

    except Exception as error:
        raise HistoricalDataError(
            "Earth Engine could not check "
            "historical Landsat availability."
        ) from error


# ==========================================================
# SENSOR DISCOVERY
# ==========================================================

def find_available_sensors(
    area,
    window,
):

    available = []

    for sensor in LANDSAT_COLLECTIONS:

        collection = (
            _build_collection(
                sensor,
                area,
                window,
            )
        )

        count = _collection_count(
            collection
        )

        if count > 0:

            available.append(
                {
                    "sensor":
                        sensor,

                    "collection":
                        collection,

                    "count":
                        count,
                }
            )

    return available


# ==========================================================
# NORMALIZATION / COMPOSITE
# ==========================================================

def _normalize_collection(
    sensor,
    collection,
):
    """
    Rename corresponding Landsat optical bands into
    a common schema.

    This provides practical spectral comparability, but
    it is not a claim of perfect cross-sensor radiometric
    harmonization.
    """

    def normalize(image):

        return image.select(
            [
                sensor["blue"],
                sensor["green"],
                sensor["red"],
                sensor["nir"],
                sensor["swir1"],
            ],
            [
                "blue",
                "green",
                "red",
                "nir",
                "swir1",
            ],
        )

    return collection.map(
        normalize
    )


def _build_composite(
    available_sensors,
    area,
):

    normalized_collections = []

    sensor_metadata = []

    for item in available_sensors:

        sensor = item[
            "sensor"
        ]

        collection = (
            _normalize_collection(
                sensor,
                item["collection"],
            )
        )

        normalized_collections.append(
            collection
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
# SPECTRAL INDICES
# ==========================================================

def _add_indices(image):
    """
    Add common Landsat spectral indices.

    NDVI:
        vegetation-related spectral signal

    MNDWI:
        water-related spectral signal

    NDBI:
        built/bare-related spectral signal

    NDBI is NOT treated as a direct building classifier.
    """

    ndvi = (
        image
        .normalizedDifference(
            [
                "nir",
                "red",
            ]
        )
        .rename("NDVI")
    )

    mndwi = (
        image
        .normalizedDifference(
            [
                "green",
                "swir1",
            ]
        )
        .rename("MNDWI")
    )

    ndbi = (
        image
        .normalizedDifference(
            [
                "swir1",
                "nir",
            ]
        )
        .rename("NDBI")
    )

    return image.addBands(
        [
            ndvi,
            mndwi,
            ndbi,
        ]
    )


# ==========================================================
# VALID COMPARABLE PIXELS
# ==========================================================

def _valid_mask(image):
    """
    Require all five common optical bands to be valid.
    """

    return (
        image
        .select(
            [
                "blue",
                "green",
                "red",
                "nir",
                "swir1",
            ]
        )
        .mask()
        .reduce(
            ee.Reducer.min()
        )
    )


# ==========================================================
# STATISTICS
# ==========================================================

def _calculate_spectral_statistics(
    before,
    after,
    area,
):

    before_valid = (
        _valid_mask(
            before
        )
    )

    after_valid = (
        _valid_mask(
            after
        )
    )

    comparable = (
        before_valid
        .And(after_valid)
    )

    before_indices = (
        _add_indices(
            before
        )
        .select(
            [
                "NDVI",
                "MNDWI",
                "NDBI",
            ]
        )
        .updateMask(
            comparable
        )
    )

    after_indices = (
        _add_indices(
            after
        )
        .select(
            [
                "NDVI",
                "MNDWI",
                "NDBI",
            ]
        )
        .updateMask(
            comparable
        )
    )

    before_named = (
        before_indices.rename(
            [
                "before_ndvi",
                "before_mndwi",
                "before_ndbi",
            ]
        )
    )

    after_named = (
        after_indices.rename(
            [
                "after_ndvi",
                "after_mndwi",
                "after_ndbi",
            ]
        )
    )

    index_image = ee.Image.cat(
        [
            before_named,
            after_named,
        ]
    )

    try:

        means = (
            index_image
            .reduceRegion(
                reducer=(
                    ee.Reducer.mean()
                ),
                geometry=area,
                scale=30,
                maxPixels=1e9,
                tileScale=4,
            )
            .getInfo()
        )

        km2 = (
            ee.Image.pixelArea()
            .divide(1e6)
        )

        comparable_area = (
            km2
            .updateMask(
                comparable
            )
            .reduceRegion(
                reducer=(
                    ee.Reducer.sum()
                ),
                geometry=area,
                scale=30,
                maxPixels=1e9,
                tileScale=4,
            )
            .get("area")
        )

        if comparable_area is None:

            comparable_area_km2 = (
                0.0
            )

        else:

            comparable_area_km2 = float(
                comparable_area.getInfo()
            )

        total_area_km2 = float(
            area
            .area()
            .divide(1e6)
            .getInfo()
        )

    except Exception as error:

        raise HistoricalDataError(
            "Earth Engine could not calculate "
            "historical spectral statistics."
        ) from error

    if total_area_km2 > 0:

        coverage_percent = (
            comparable_area_km2
            / total_area_km2
            * 100
        )

    else:

        coverage_percent = 0.0

    def value(name):

        item = means.get(
            name
        )

        if item is None:
            return None

        return float(item)

    before_ndvi = value(
        "before_ndvi"
    )

    after_ndvi = value(
        "after_ndvi"
    )

    before_mndwi = value(
        "before_mndwi"
    )

    after_mndwi = value(
        "after_mndwi"
    )

    before_ndbi = value(
        "before_ndbi"
    )

    after_ndbi = value(
        "after_ndbi"
    )

    if (
        before_ndvi is None
        or after_ndvi is None
        or before_mndwi is None
        or after_mndwi is None
        or before_ndbi is None
        or after_ndbi is None
    ):

        raise HistoricalDataError(
            "Insufficient valid Landsat pixels were "
            "available for spectral comparison."
        )

    return {
        "total_area_km2":
            total_area_km2,

        "comparable_area_km2":
            comparable_area_km2,

        "coverage_percent":
            coverage_percent,

        "before_mean_ndvi":
            before_ndvi,

        "after_mean_ndvi":
            after_ndvi,

        "ndvi_change":
            (
                after_ndvi
                - before_ndvi
            ),

        "before_mean_mndwi":
            before_mndwi,

        "after_mean_mndwi":
            after_mndwi,

        "mndwi_change":
            (
                after_mndwi
                - before_mndwi
            ),

        "before_mean_ndbi":
            before_ndbi,

        "after_mean_ndbi":
            after_ndbi,

        "ndbi_change":
            (
                after_ndbi
                - before_ndbi
            ),
    }


# ==========================================================
# PUBLIC HISTORICAL ANALYSIS
# ==========================================================

def analyze_historical_area(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
):
    """
    Perform a common Landsat spectral comparison.

    This function does NOT claim Dynamic World classes,
    ML confidence, exact built-up area, or ground truth.
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

    before_window = (
        _date_window(
            request[
                "before_date"
            ]
        )
    )

    after_window = (
        _date_window(
            request[
                "after_date"
            ]
        )
    )

    before_available = (
        find_available_sensors(
            area,
            before_window,
        )
    )

    after_available = (
        find_available_sensors(
            area,
            after_window,
        )
    )

    if not before_available:

        raise HistoricalDataError(
            "No supported Landsat observations "
            "were found for the BEFORE window."
        )

    if not after_available:

        raise HistoricalDataError(
            "No supported Landsat observations "
            "were found for the AFTER window."
        )

    (
        before_composite,
        before_sensors,
    ) = _build_composite(
        before_available,
        area,
    )

    (
        after_composite,
        after_sensors,
    ) = _build_composite(
        after_available,
        area,
    )

    stats = (
        _calculate_spectral_statistics(
            before_composite,
            after_composite,
            area,
        )
    )

    warnings = []

    before_has_l7 = any(
        sensor["name"]
        == "Landsat 7"

        for sensor
        in before_sensors
    )

    after_has_l7 = any(
        sensor["name"]
        == "Landsat 7"

        for sensor
        in after_sensors
    )

    if (
        before_has_l7
        or after_has_l7
    ):

        warnings.append(
            "This comparison includes Landsat 7. "
            "Post-2003 scan-line gaps can affect "
            "spatial completeness despite multi-scene "
            "compositing."
        )

    warnings.append(
        "Historical mode compares Landsat spectral "
        "indices across sensor generations. Bandpass "
        "differences can influence absolute index values."
    )

    warnings.append(
        "NDBI is a built/bare spectral indicator and "
        "must not be interpreted as exact built-up area."
    )

    if (
        stats[
            "coverage_percent"
        ]
        < 20
    ):

        warnings.append(
            "Comparable Landsat coverage is very low. "
            "Broad area-level conclusions are not "
            "supported."
        )

    return {
        "analysis_mode":
            "historical_spectral",

        "method":
            (
                "Cloud-masked Landsat spectral "
                "comparison"
            ),

        "approximate_resolution_m":
            30,

        "before_window":
            before_window,

        "after_window":
            after_window,

        "before_sensors":
            before_sensors,

        "after_sensors":
            after_sensors,

        "warnings":
            warnings,

        **stats,
    }


# ==========================================================
# HISTORICAL IMAGERY
# ==========================================================

def get_historical_satellite_images(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
):
    """
    Generate BEFORE/AFTER Landsat true-color previews.
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

    before_window = (
        _date_window(
            request[
                "before_date"
            ]
        )
    )

    after_window = (
        _date_window(
            request[
                "after_date"
            ]
        )
    )

    before_available = (
        find_available_sensors(
            area,
            before_window,
        )
    )

    after_available = (
        find_available_sensors(
            area,
            after_window,
        )
    )

    if not before_available:

        raise HistoricalDataError(
            "No supported Landsat observations "
            "were found for the BEFORE window."
        )

    if not after_available:

        raise HistoricalDataError(
            "No supported Landsat observations "
            "were found for the AFTER window."
        )

    (
        before_composite,
        before_sensors,
    ) = _build_composite(
        before_available,
        area,
    )

    (
        after_composite,
        after_sensors,
    ) = _build_composite(
        after_available,
        area,
    )

    visualization = {
        "bands": [
            "red",
            "green",
            "blue",
        ],

        "min":
            0.0,

        "max":
            0.30,

        "gamma":
            1.1,
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
        "region":
            area,

        "dimensions":
            700,

        "format":
            "png",
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
            "Earth Engine could not generate "
            "historical Landsat preview images."
        ) from error

    before_observations = sum(
        sensor[
            "observations"
        ]

        for sensor
        in before_sensors
    )

    after_observations = sum(
        sensor[
            "observations"
        ]

        for sensor
        in after_sensors
    )

    return {
        "analysis_mode":
            "historical_spectral",

        "before_url":
            before_url,

        "after_url":
            after_url,

        "before_observations":
            before_observations,

        "after_observations":
            after_observations,

        "before_sensors":
            before_sensors,

        "after_sensors":
            after_sensors,

        "before_window":
            before_window,

        "after_window":
            after_window,
    }