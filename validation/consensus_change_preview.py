import ee
from pathlib import Path


PROJECT_ID = "optimum-reactor-510109-b5"

ee.Initialize(project=PROJECT_ID)


# ==========================================================
# TEST CONFIGURATION
# ==========================================================

LATITUDE = 28.6139
LONGITUDE = 77.2090

BEFORE_DATE = "2022-09-15"
AFTER_DATE = "2025-09-15"

RADIUS_KM = 5

PROBABILITY_THRESHOLD = 0.60
MIN_CONFIDENCE_FREQUENCY = 0.50
MIN_CONSENSUS = 0.60
MIN_CONFIDENT_OBSERVATIONS = 2


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
# STUDY AREA
# ==========================================================

area = (
    ee.Geometry.Point(
        [
            LONGITUDE,
            LATITUDE,
        ]
    )
    .buffer(
        RADIUS_KM * 1000
    )
)


# ==========================================================
# DYNAMIC WORLD
# ==========================================================

def build_collection(
    target_date,
):
    """
    Build one Dynamic World composite-window collection.
    """

    target = ee.Date(
        target_date
    )

    return (
        ee.ImageCollection(
            "GOOGLE/DYNAMICWORLD/V1"
        )
        .filterBounds(area)
        .filterDate(
            target.advance(
                -45,
                "day",
            ),
            target.advance(
                45,
                "day",
            ),
        )
    )


def process_observation(image):
    """
    Convert one Dynamic World probability image into:

    available
        Pixel has Dynamic World data.

    confident
        Maximum class probability >= 0.60.

    label
        Most likely class, retained only where confident.
    """

    probabilities = (
        image.select(
            PROBABILITY_BANDS
        )
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
            PROBABILITY_THRESHOLD
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


def build_consensus(
    collection,
):
    """
    Build temporal consensus classification.
    """

    processed = (
        collection.map(
            process_observation
        )
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

    def agreement(image):
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
    )

    confidence_frequency = (
        confident_count
        .divide(
            available_count.max(1)
        )
    )

    consensus_fraction = (
        agreement_count
        .divide(
            confident_count.max(1)
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
                MIN_CONSENSUS
            )
        )
    )

    return {
        "land":
            mode_label,

        "valid":
            valid,
    }


# ==========================================================
# BUILD BEFORE / AFTER CONSENSUS
# ==========================================================

before_collection = (
    build_collection(
        BEFORE_DATE
    )
)

after_collection = (
    build_collection(
        AFTER_DATE
    )
)


before = (
    build_consensus(
        before_collection
    )
)

after = (
    build_consensus(
        after_collection
    )
)


comparable = (
    before[
        "valid"
    ]
    .And(
        after[
            "valid"
        ]
    )
)


before_land = (
    before[
        "land"
    ]
    .updateMask(
        comparable
    )
)


after_land = (
    after[
        "land"
    ]
    .updateMask(
        comparable
    )
)


# ==========================================================
# GROUPED CLASSES
# ==========================================================

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


before_built = (
    before_land.eq(6)
)


after_built = (
    after_land.eq(6)
)


before_bare = (
    before_land.eq(7)
)


before_water = (
    before_land.eq(0)
)


after_water = (
    after_land.eq(0)
)


# ==========================================================
# TRANSITIONS
# ==========================================================

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


nonwater_to_water = (
    before_land
    .neq(0)
    .And(
        after_water
    )
)


water_to_nonwater = (
    before_water
    .And(
        after_land.neq(0)
    )
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


# ==========================================================
# VISUAL ENLARGEMENT ONLY
# ==========================================================

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


# ==========================================================
# SENTINEL-2 BACKGROUND
# ==========================================================

def mask_clouds(image):

    scl = (
        image.select(
            "SCL"
        )
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


after_target = (
    ee.Date(
        AFTER_DATE
    )
)


sentinel = (
    ee.ImageCollection(
        "COPERNICUS/S2_SR_HARMONIZED"
    )
    .filterBounds(area)
    .filterDate(
        after_target.advance(
            -45,
            "day",
        ),
        after_target.advance(
            45,
            "day",
        ),
    )
    .filter(
        ee.Filter.lt(
            "CLOUDY_PIXEL_PERCENTAGE",
            90,
        )
    )
    .map(
        mask_clouds
    )
)


background = (
    sentinel
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
    .blend(
        colored_changes
    )
    .clip(area)
)


# ==========================================================
# GENERATE URL
# ==========================================================

thumbnail_params = {
    "region":
        area,

    "dimensions":
        1000,

    "format":
        "png",
}


url = (
    final_map
    .getThumbURL(
        thumbnail_params
    )
)


print()
print(
    "SetQuery AI consensus preview"
)

print(
    "Location: New Delhi"
)

print(
    "Before:",
    BEFORE_DATE
)

print(
    "After:",
    AFTER_DATE
)

print()

print(
    "Open this URL in your browser:"
)

print()
print(url)

print()

print(
    "Legend:"
)

print(
    "RED    = Vegetation -> Built"
)

print(
    "GREEN  = Built -> Vegetation"
)

print(
    "YELLOW = Bare -> Built"
)

print(
    "BLUE   = Non-water -> Water"
)

print(
    "ORANGE = Water -> Non-water"
)