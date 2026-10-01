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

MIN_CONFIDENT_OBSERVATIONS = 2
MIN_CONFIDENCE_FREQUENCY = 0.50
MIN_TEMPORAL_CONSENSUS = 0.60

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

ee.Initialize(
    project=PROJECT_ID
)


# ==========================================================
# CUSTOM ERRORS
# ==========================================================

class AnalysisValidationError(ValueError):
    """Raised when an analysis request is invalid."""


class AnalysisDataError(RuntimeError):
    """Raised when required Earth Engine data is unavailable."""


# ==========================================================
# VALIDATION
# ==========================================================

def _parse_date(
    value,
    field_name,
):
    """Convert a date or YYYY-MM-DD string to Python date."""

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    try:
        return datetime.strptime(
            str(value),
            "%Y-%m-%d",
        ).date()

    except (
        TypeError,
        ValueError,
    ) as error:

        raise AnalysisValidationError(
            f"{field_name} must use YYYY-MM-DD format."
        ) from error


def _validate_coordinates(
    latitude,
    longitude,
):
    """Validate latitude and longitude."""

    try:
        latitude = float(latitude)
        longitude = float(longitude)

    except (
        TypeError,
        ValueError,
    ) as error:

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

    return (
        latitude,
        longitude,
    )


def _validate_radius(
    radius_km,
):
    """Validate analysis radius."""

    try:
        radius_km = float(radius_km)

    except (
        TypeError,
        ValueError,
    ) as error:

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


def _validate_confidence_threshold(
    confidence_threshold,
):
    """Validate Dynamic World probability threshold."""

    try:
        confidence_threshold = float(
            confidence_threshold
        )

    except (
        TypeError,
        ValueError,
    ) as error:

        raise AnalysisValidationError(
            "Confidence threshold must be numeric."
        ) from error

    if not (
        0
        < confidence_threshold
        <= 1
    ):
        raise AnalysisValidationError(
            "Confidence threshold must be greater "
            "than 0 and no greater than 1."
        )

    return confidence_threshold


def _build_window_metadata(
    target_date,
):
    """
    Build requested and effective composite-window metadata.

    Earth Engine filterDate uses an inclusive start and
    exclusive end.
    """

    today = date.today()

    requested_start = (
        target_date
        - timedelta(
            days=COMPOSITE_WINDOW_DAYS
        )
    )

    requested_end_exclusive = (
        target_date
        + timedelta(
            days=COMPOSITE_WINDOW_DAYS
        )
    )

    tomorrow = (
        today
        + timedelta(
            days=1
        )
    )

    effective_start = requested_start

    effective_end_exclusive = min(
        requested_end_exclusive,
        tomorrow,
    )

    future_truncated = (
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
            future_truncated,
    }


def validate_analysis_request(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """Validate a Modern ML analysis request."""

    (
        latitude,
        longitude,
    ) = _validate_coordinates(
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
        after
        - before
    ).days

    if (
        separation_days
        < MIN_DATE_SEPARATION_DAYS
    ):
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

    if before_window[
        "future_truncated"
    ]:
        warnings.append(
            "The BEFORE composite window extends beyond "
            "today and was truncated to currently "
            "available dates."
        )

    if after_window[
        "future_truncated"
    ]:
        warnings.append(
            "The AFTER composite window extends beyond "
            "today and was truncated to currently "
            "available dates."
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


# ==========================================================
# GENERAL EARTH ENGINE HELPERS
# ==========================================================

def _create_area(
    latitude,
    longitude,
    radius_km,
):
    """Create study geometry."""

    point = ee.Geometry.Point(
        [
            longitude,
            latitude,
        ]
    )

    return point.buffer(
        radius_km * 1000
    )


def _get_collection_count(
    collection,
    label,
):
    """Retrieve an Earth Engine collection count."""

    try:
        return int(
            collection
            .size()
            .getInfo()
        )

    except Exception as error:

        raise AnalysisDataError(
            f"Could not check {label} observations. "
            "Earth Engine or the network may be "
            "temporarily unavailable."
        ) from error


def _observation_warnings(
    before_count,
    after_count,
    dataset_name,
):
    """Generate warnings for unusually small collections."""

    warnings = []

    if (
        before_count
        < LOW_OBSERVATION_WARNING_COUNT
    ):
        warnings.append(
            f"Only {before_count} {dataset_name} "
            "observation(s) were available for the "
            "BEFORE period."
        )

    if (
        after_count
        < LOW_OBSERVATION_WARNING_COUNT
    ):
        warnings.append(
            f"Only {after_count} {dataset_name} "
            "observation(s) were available for the "
            "AFTER period."
        )

    return warnings


# ==========================================================
# DYNAMIC WORLD COLLECTION
# ==========================================================

def _build_dynamic_world_collection(
    area,
    window,
):
    """Build Dynamic World collection for one period."""

    return (
        ee.ImageCollection(
            DYNAMIC_WORLD_COLLECTION
        )
        .filterBounds(
            area
        )
        .filterDate(
            window[
                "effective_start"
            ],
            window[
                "effective_end_exclusive"
            ],
        )
    )


# ==========================================================
# SENTINEL-2
# ==========================================================

def _mask_sentinel_clouds(
    image,
):
    """Mask selected Sentinel-2 SCL classes."""

    scl = image.select(
        "SCL"
    )

    mask = (
        scl.neq(3)
        .And(
            scl.neq(8)
        )
        .And(
            scl.neq(9)
        )
        .And(
            scl.neq(10)
        )
        .And(
            scl.neq(11)
        )
    )

    return image.updateMask(
        mask
    )


def _build_sentinel_collection(
    area,
    window,
):
    """Build cloud-masked Sentinel-2 SR collection."""

    return (
        ee.ImageCollection(
            SENTINEL_COLLECTION
        )
        .filterBounds(
            area
        )
        .filterDate(
            window[
                "effective_start"
            ],
            window[
                "effective_end_exclusive"
            ],
        )
        .filter(
            ee.Filter.lt(
                "CLOUDY_PIXEL_PERCENTAGE",
                90,
            )
        )
        .map(
            _mask_sentinel_clouds
        )
    )


# ==========================================================
# TEMPORAL CONSENSUS
# ==========================================================

def _process_dynamic_world_observation(
    image,
    confidence_threshold,
):
    """Process one Dynamic World observation."""

    probabilities = image.select(
        PROBABILITY_BANDS
    )

    available = (
        probabilities
        .mask()
        .reduce(
            ee.Reducer.min()
        )
        .rename(
            "available"
        )
    )

    confidence = (
        probabilities
        .reduce(
            ee.Reducer.max()
        )
        .rename(
            "confidence"
        )
    )

    label = (
        probabilities
        .toArray()
        .arrayArgmax()
        .arrayGet([0])
        .rename(
            "label"
        )
    )

    confident = (
        confidence
        .gte(
            confidence_threshold
        )
        .And(
            available
        )
        .rename(
            "confident"
        )
    )

    confident_label = (
        label
        .updateMask(
            confident
        )
        .rename(
            "label"
        )
    )

    return ee.Image.cat(
        [
            confident_label,

            confident
            .unmask(0)
            .rename(
                "confident"
            ),

            available
            .unmask(0)
            .rename(
                "available"
            ),
        ]
    )


def _build_temporal_consensus(
    collection,
    confidence_threshold,
):
    """
    Build Dynamic World temporal-consensus classification.

    Methodology is unchanged from the pre-optimization
    implementation.
    """

    def process(
        image,
    ):
        return (
            _process_dynamic_world_observation(
                image,
                confidence_threshold,
            )
        )

    processed = collection.map(
        process
    )

    available_count = (
        processed
        .select(
            "available"
        )
        .sum()
        .rename(
            "available_count"
        )
    )

    confident_count = (
        processed
        .select(
            "confident"
        )
        .sum()
        .rename(
            "confident_count"
        )
    )

    mode_label = (
        processed
        .select(
            "label"
        )
        .reduce(
            ee.Reducer.mode()
        )
        .rename(
            "land"
        )
    )

    def agreement(
        image,
    ):
        return (
            image
            .select(
                "label"
            )
            .eq(
                mode_label
            )
            .unmask(0)
            .rename(
                "agreement"
            )
        )

    agreement_count = (
        processed
        .map(
            agreement
        )
        .sum()
        .rename(
            "agreement_count"
        )
    )

    confidence_frequency = (
        confident_count
        .divide(
            available_count.max(1)
        )
        .rename(
            "confidence_frequency"
        )
    )

    consensus_fraction = (
        agreement_count
        .divide(
            confident_count.max(1)
        )
        .rename(
            "consensus_fraction"
        )
    )

    valid = (
        available_count
        .gte(
            MIN_CONFIDENT_OBSERVATIONS
        )
        .And(
            confident_count
            .gte(
                MIN_CONFIDENT_OBSERVATIONS
            )
        )
        .And(
            confidence_frequency
            .gte(
                MIN_CONFIDENCE_FREQUENCY
            )
        )
        .And(
            consensus_fraction
            .gte(
                MIN_TEMPORAL_CONSENSUS
            )
        )
        .rename(
            "valid"
        )
    )

    return {
        "land":
            mode_label,

        "valid":
            valid,

        "available_count":
            available_count,

        "confident_count":
            confident_count,

        "confidence_frequency":
            confidence_frequency,

        "consensus_fraction":
            consensus_fraction,
    }


# ==========================================================
# SHARED MODERN CONTEXT
# ==========================================================

def prepare_modern_analysis(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """
    Build the shared Modern analysis context once.

    The routed application path reuses this context for:
    - numerical analysis;
    - Sentinel-2 previews;
    - Change Map generation.

    This avoids rebuilding and recounting the same
    Dynamic World and Sentinel-2 collections.
    """

    request = validate_analysis_request(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=confidence_threshold,
    )

    area = _create_area(
        request[
            "latitude"
        ],
        request[
            "longitude"
        ],
        request[
            "radius_km"
        ],
    )

    # ------------------------------------------------------
    # DYNAMIC WORLD
    # ------------------------------------------------------

    before_dw_collection = (
        _build_dynamic_world_collection(
            area,
            request[
                "before_window"
            ],
        )
    )

    after_dw_collection = (
        _build_dynamic_world_collection(
            area,
            request[
                "after_window"
            ],
        )
    )

    before_dw_count = (
        _get_collection_count(
            before_dw_collection,
            "Dynamic World BEFORE",
        )
    )

    after_dw_count = (
        _get_collection_count(
            after_dw_collection,
            "Dynamic World AFTER",
        )
    )

    if before_dw_count == 0:
        raise AnalysisDataError(
            "No Dynamic World observations were found "
            "for the BEFORE composite window."
        )

    if after_dw_count == 0:
        raise AnalysisDataError(
            "No Dynamic World observations were found "
            "for the AFTER composite window."
        )

    before_consensus = (
        _build_temporal_consensus(
            before_dw_collection,
            request[
                "confidence_threshold"
            ],
        )
    )

    after_consensus = (
        _build_temporal_consensus(
            after_dw_collection,
            request[
                "confidence_threshold"
            ],
        )
    )

    comparable = (
        before_consensus[
            "valid"
        ]
        .And(
            after_consensus[
                "valid"
            ]
        )
    )

    before_land = (
        before_consensus[
            "land"
        ]
        .updateMask(
            comparable
        )
    )

    after_land = (
        after_consensus[
            "land"
        ]
        .updateMask(
            comparable
        )
    )

    # ------------------------------------------------------
    # GROUPED CLASSES
    # ------------------------------------------------------

    before_vegetation = (
        before_land
        .gte(1)
        .And(
            before_land.lte(5)
        )
    )

    after_vegetation = (
        after_land
        .gte(1)
        .And(
            after_land.lte(5)
        )
    )

    before_water = (
        before_land.eq(0)
    )

    after_water = (
        after_land.eq(0)
    )

    before_built = (
        before_land.eq(6)
    )

    after_built = (
        after_land.eq(6)
    )

    before_bare = (
        before_land.eq(7)
    )

    after_bare = (
        after_land.eq(7)
    )

    # ------------------------------------------------------
    # TRANSITIONS
    # ------------------------------------------------------

    vegetation_to_built = (
        before_vegetation
        .And(
            after_built
        )
    )

    built_to_vegetation = (
        before_built
        .And(
            after_vegetation
        )
    )

    bare_to_built = (
        before_bare
        .And(
            after_built
        )
    )

    water_to_nonwater = (
        before_water
        .And(
            after_land.neq(0)
        )
    )

    nonwater_to_water = (
        before_land
        .neq(0)
        .And(
            after_water
        )
    )

    # ------------------------------------------------------
    # SENTINEL-2
    # ------------------------------------------------------

    before_sentinel_collection = (
        _build_sentinel_collection(
            area,
            request[
                "before_window"
            ],
        )
    )

    after_sentinel_collection = (
        _build_sentinel_collection(
            area,
            request[
                "after_window"
            ],
        )
    )

    before_sentinel_count = (
        _get_collection_count(
            before_sentinel_collection,
            "Sentinel-2 BEFORE",
        )
    )

    after_sentinel_count = (
        _get_collection_count(
            after_sentinel_collection,
            "Sentinel-2 AFTER",
        )
    )

    if before_sentinel_count == 0:
        raise AnalysisDataError(
            "No usable Sentinel-2 observations were found "
            "for the BEFORE composite window."
        )

    if after_sentinel_count == 0:
        raise AnalysisDataError(
            "No usable Sentinel-2 observations were found "
            "for the AFTER composite window."
        )

    return {
        "request":
            request,

        "area":
            area,

        "before_dw_collection":
            before_dw_collection,

        "after_dw_collection":
            after_dw_collection,

        "before_dw_count":
            before_dw_count,

        "after_dw_count":
            after_dw_count,

        "before_consensus":
            before_consensus,

        "after_consensus":
            after_consensus,

        "comparable":
            comparable,

        "before_land":
            before_land,

        "after_land":
            after_land,

        "before_vegetation":
            before_vegetation,

        "after_vegetation":
            after_vegetation,

        "before_water":
            before_water,

        "after_water":
            after_water,

        "before_built":
            before_built,

        "after_built":
            after_built,

        "before_bare":
            before_bare,

        "after_bare":
            after_bare,

        "vegetation_to_built":
            vegetation_to_built,

        "built_to_vegetation":
            built_to_vegetation,

        "bare_to_built":
            bare_to_built,

        "water_to_nonwater":
            water_to_nonwater,

        "nonwater_to_water":
            nonwater_to_water,

        "before_sentinel_collection":
            before_sentinel_collection,

        "after_sentinel_collection":
            after_sentinel_collection,

        "before_sentinel_count":
            before_sentinel_count,

        "after_sentinel_count":
            after_sentinel_count,
    }


# ==========================================================
# NUMERICAL ANALYSIS FROM SHARED CONTEXT
# ==========================================================

def analyze_prepared_area(
    context,
):
    """Calculate statistics from a prepared Modern context."""

    request = context[
        "request"
    ]

    area = context[
        "area"
    ]

    km2 = (
        ee.Image.pixelArea()
        .divide(1e6)
    )

    stats_image = ee.Image.cat(
        [
            km2
            .updateMask(
                context[
                    "comparable"
                ]
            )
            .rename(
                "comparable"
            ),

            km2
            .updateMask(
                context[
                    "before_vegetation"
                ]
            )
            .rename(
                "before_vegetation"
            ),

            km2
            .updateMask(
                context[
                    "after_vegetation"
                ]
            )
            .rename(
                "after_vegetation"
            ),

            km2
            .updateMask(
                context[
                    "before_water"
                ]
            )
            .rename(
                "before_water"
            ),

            km2
            .updateMask(
                context[
                    "after_water"
                ]
            )
            .rename(
                "after_water"
            ),

            km2
            .updateMask(
                context[
                    "before_built"
                ]
            )
            .rename(
                "before_built"
            ),

            km2
            .updateMask(
                context[
                    "after_built"
                ]
            )
            .rename(
                "after_built"
            ),

            km2
            .updateMask(
                context[
                    "before_bare"
                ]
            )
            .rename(
                "before_bare"
            ),

            km2
            .updateMask(
                context[
                    "after_bare"
                ]
            )
            .rename(
                "after_bare"
            ),

            km2
            .updateMask(
                context[
                    "vegetation_to_built"
                ]
            )
            .rename(
                "vegetation_to_built"
            ),

            km2
            .updateMask(
                context[
                    "built_to_vegetation"
                ]
            )
            .rename(
                "built_to_vegetation"
            ),

            km2
            .updateMask(
                context[
                    "bare_to_built"
                ]
            )
            .rename(
                "bare_to_built"
            ),

            km2
            .updateMask(
                context[
                    "water_to_nonwater"
                ]
            )
            .rename(
                "water_to_nonwater"
            ),

            km2
            .updateMask(
                context[
                    "nonwater_to_water"
                ]
            )
            .rename(
                "nonwater_to_water"
            ),
        ]
    )

    try:
        stats = (
            stats_image
            .reduceRegion(
                reducer=(
                    ee.Reducer.sum()
                ),
                geometry=area,
                scale=10,
                maxPixels=1e9,
                tileScale=4,
            )
            .getInfo()
        )

        total_area_km2 = float(
            area
            .area()
            .divide(1e6)
            .getInfo()
        )

    except Exception as error:

        raise AnalysisDataError(
            "Earth Engine could not calculate "
            "land-cover statistics."
        ) from error

    def stat_value(
        name,
    ):
        value = stats.get(
            name
        )

        if value is None:
            return 0.0

        return float(
            value
        )

    comparable_area_km2 = (
        stat_value(
            "comparable"
        )
    )

    if total_area_km2 > 0:
        coverage_percent = (
            comparable_area_km2
            / total_area_km2
            * 100
        )

    else:
        coverage_percent = 0.0

    warnings = list(
        request[
            "warnings"
        ]
    )

    warnings.extend(
        _observation_warnings(
            context[
                "before_dw_count"
            ],
            context[
                "after_dw_count"
            ],
            "Dynamic World",
        )
    )

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

    return {
        "before_observations":
            context[
                "before_dw_count"
            ],

        "after_observations":
            context[
                "after_dw_count"
            ],

        "total_area_km2":
            total_area_km2,

        "comparable_area_km2":
            comparable_area_km2,

        "coverage_percent":
            coverage_percent,

        "before_vegetation_km2":
            stat_value(
                "before_vegetation"
            ),

        "after_vegetation_km2":
            stat_value(
                "after_vegetation"
            ),

        "before_built_km2":
            stat_value(
                "before_built"
            ),

        "after_built_km2":
            stat_value(
                "after_built"
            ),

        "before_water_km2":
            stat_value(
                "before_water"
            ),

        "after_water_km2":
            stat_value(
                "after_water"
            ),

        "before_bare_km2":
            stat_value(
                "before_bare"
            ),

        "after_bare_km2":
            stat_value(
                "after_bare"
            ),

        "vegetation_to_built_km2":
            stat_value(
                "vegetation_to_built"
            ),

        "built_to_vegetation_km2":
            stat_value(
                "built_to_vegetation"
            ),

        "bare_to_built_km2":
            stat_value(
                "bare_to_built"
            ),

        "water_to_nonwater_km2":
            stat_value(
                "water_to_nonwater"
            ),

        "nonwater_to_water_km2":
            stat_value(
                "nonwater_to_water"
            ),

        "classification_method":
            "dynamic_world_temporal_consensus",

        "confidence_threshold":
            request[
                "confidence_threshold"
            ],

        "min_confident_observations":
            MIN_CONFIDENT_OBSERVATIONS,

        "min_confidence_frequency":
            MIN_CONFIDENCE_FREQUENCY,

        "min_temporal_consensus":
            MIN_TEMPORAL_CONSENSUS,

        "date_separation_days":
            request[
                "date_separation_days"
            ],

        "before_window":
            request[
                "before_window"
            ],

        "after_window":
            request[
                "after_window"
            ],

        "warnings":
            warnings,
    }


# ==========================================================
# SENTINEL PREVIEWS FROM SHARED CONTEXT
# ==========================================================

def get_prepared_satellite_images(
    context,
):
    """Generate true-color previews from shared context."""

    request = context[
        "request"
    ]

    area = context[
        "area"
    ]

    before_image = (
        context[
            "before_sentinel_collection"
        ]
        .median()
        .clip(
            area
        )
    )

    after_image = (
        context[
            "after_sentinel_collection"
        ]
        .median()
        .clip(
            area
        )
    )

    rgb_vis = {
        "bands": [
            "B4",
            "B3",
            "B2",
        ],
        "min":
            0,
        "max":
            3000,
        "gamma":
            1.1,
    }

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
            before_image
            .visualize(
                **rgb_vis
            )
            .getThumbURL(
                thumbnail_params
            )
        )

        after_url = (
            after_image
            .visualize(
                **rgb_vis
            )
            .getThumbURL(
                thumbnail_params
            )
        )

    except Exception as error:

        raise AnalysisDataError(
            "Earth Engine could not generate "
            "Sentinel-2 preview images."
        ) from error

    warnings = list(
        request[
            "warnings"
        ]
    )

    warnings.extend(
        _observation_warnings(
            context[
                "before_sentinel_count"
            ],
            context[
                "after_sentinel_count"
            ],
            "Sentinel-2",
        )
    )

    return {
        "before_url":
            before_url,

        "after_url":
            after_url,

        "before_sentinel_observations":
            context[
                "before_sentinel_count"
            ],

        "after_sentinel_observations":
            context[
                "after_sentinel_count"
            ],

        "before_window":
            request[
                "before_window"
            ],

        "after_window":
            request[
                "after_window"
            ],

        "warnings":
            warnings,
    }


# ==========================================================
# CHANGE MAP FROM SHARED CONTEXT
# ==========================================================

def get_prepared_change_map(
    context,
):
    """
    Generate the transition map from shared context.

    focal_max is used only for display. Numerical statistics
    continue to use the original transition pixels.
    """

    request = context[
        "request"
    ]

    area = context[
        "area"
    ]

    change = (
        ee.Image(0)
        .where(
            context[
                "vegetation_to_built"
            ],
            1,
        )
        .where(
            context[
                "built_to_vegetation"
            ],
            2,
        )
        .where(
            context[
                "bare_to_built"
            ],
            3,
        )
        .where(
            context[
                "nonwater_to_water"
            ],
            4,
        )
        .where(
            context[
                "water_to_nonwater"
            ],
            5,
        )
        .clip(
            area
        )
    )

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
        .clip(
            area
        )
    )

    background = (
        context[
            "after_sentinel_collection"
        ]
        .median()
        .clip(
            area
        )
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
        .multiply(
            0.45
        )
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
        .blend(
            colored_changes
        )
        .clip(
            area
        )
    )

    thumbnail_params = {
        "region":
            area,

        "dimensions":
            800,

        "format":
            "png",
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
            "Earth Engine could not generate "
            "the change-map preview."
        ) from error

    return {
        "change_url":
            change_url,

        "before_change_observations":
            context[
                "before_dw_count"
            ],

        "after_change_observations":
            context[
                "after_dw_count"
            ],

        "background_sentinel_observations":
            context[
                "after_sentinel_count"
            ],

        "classification_method":
            "dynamic_world_temporal_consensus",

        "confidence_threshold":
            request[
                "confidence_threshold"
            ],

        "min_confident_observations":
            MIN_CONFIDENT_OBSERVATIONS,

        "min_confidence_frequency":
            MIN_CONFIDENCE_FREQUENCY,

        "min_temporal_consensus":
            MIN_TEMPORAL_CONSENSUS,

        "before_window":
            request[
                "before_window"
            ],

        "after_window":
            request[
                "after_window"
            ],
    }


# ==========================================================
# BACKWARD-COMPATIBLE: NUMERICAL ANALYSIS
# ==========================================================

def analyze_area(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """
    Run Modern analysis independently.

    The main routed application uses prepare_modern_analysis()
    once and calls analyze_prepared_area() instead.
    """

    context = prepare_modern_analysis(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=confidence_threshold,
    )

    return analyze_prepared_area(
        context
    )


# ==========================================================
# BACKWARD-COMPATIBLE: SENTINEL IMAGES
# ==========================================================

def get_satellite_images(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
):
    """
    Generate Sentinel-2 previews independently.

    This standalone function intentionally does not build
    Dynamic World analysis state.
    """

    request = validate_analysis_request(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=(
            DEFAULT_CONFIDENCE_THRESHOLD
        ),
    )

    area = _create_area(
        request[
            "latitude"
        ],
        request[
            "longitude"
        ],
        request[
            "radius_km"
        ],
    )

    before_collection = (
        _build_sentinel_collection(
            area,
            request[
                "before_window"
            ],
        )
    )

    after_collection = (
        _build_sentinel_collection(
            area,
            request[
                "after_window"
            ],
        )
    )

    before_count = (
        _get_collection_count(
            before_collection,
            "Sentinel-2 BEFORE",
        )
    )

    after_count = (
        _get_collection_count(
            after_collection,
            "Sentinel-2 AFTER",
        )
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

    context = {
        "request":
            request,

        "area":
            area,

        "before_sentinel_collection":
            before_collection,

        "after_sentinel_collection":
            after_collection,

        "before_sentinel_count":
            before_count,

        "after_sentinel_count":
            after_count,
    }

    return get_prepared_satellite_images(
        context
    )


# ==========================================================
# BACKWARD-COMPATIBLE: CHANGE MAP
# ==========================================================

def get_change_map(
    latitude,
    longitude,
    before_date,
    after_date,
    radius_km=10,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """
    Generate the change map independently.

    The routed application reuses a shared prepared context.
    """

    context = prepare_modern_analysis(
        latitude=latitude,
        longitude=longitude,
        before_date=before_date,
        after_date=after_date,
        radius_km=radius_km,
        confidence_threshold=confidence_threshold,
    )

    return get_prepared_change_map(
        context
    )