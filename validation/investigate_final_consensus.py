import time

import ee
from geopy.geocoders import Nominatim


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


LOCATIONS = [
    "New Delhi, India",
    "Mumbai, Maharashtra, India",
    "Ludhiana, Punjab, India",
    "Dehradun, Uttarakhand, India",
    "Bhopal, Madhya Pradesh, India",
]


BEFORE_DATE = "2022-09-15"
AFTER_DATE = "2025-09-15"

RADIUS_KM = 5

PROBABILITY_THRESHOLD = 0.60
MIN_CONFIDENCE_FREQUENCY = 0.50
MIN_CONSENSUS = 0.60
MIN_CONFIDENT_OBSERVATIONS = 2


def build_collection(
    area,
    target_date,
):
    """
    Build the Dynamic World collection around one target.
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
    Create per-observation classification information.

    available:
        This observation has Dynamic World data at the pixel.

    confident:
        Maximum class probability is >= 0.60.

    label:
        Dominant class, masked unless observation is confident.
    """

    probabilities = image.select(
        PROBABILITY_BANDS
    )

    # Require all probability bands to be available.
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

    # Convert masked availability/confidence to zero where
    # this scene has no data so sums behave predictably.
    available_unmasked = (
        available
        .unmask(0)
        .rename(
            "available"
        )
    )

    confident_unmasked = (
        confident
        .unmask(0)
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
            confident_unmasked,
            available_unmasked,
        ]
    )


def build_consensus(
    collection,
):
    """
    Build one temporally consistent classification.

    Pixel validity requires:

    - >= 2 confident observations
    - >= 50% of actually available observations confident
    - >= 60% agreement among confident classifications
    """

    processed = collection.map(
        process_observation
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

    labels = processed.select(
        "label"
    )

    mode_label = (
        labels
        .reduce(
            ee.Reducer.mode()
        )
        .rename(
            "land"
        )
    )

    def calculate_agreement(image):
        """
        Count agreement only where a confident label exists.
        """

        label = image.select(
            "label"
        )

        return (
            label
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
            calculate_agreement
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
                MIN_CONSENSUS
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


def calculate_area_km2(
    mask,
    area,
):
    """
    Calculate masked area in square kilometres.
    """

    km2 = (
        ee.Image.pixelArea()
        .divide(1e6)
    )

    value = (
        km2
        .updateMask(
            mask
        )
        .reduceRegion(
            reducer=(
                ee.Reducer.sum()
            ),
            geometry=area,
            scale=10,
            maxPixels=1e9,
            tileScale=4,
        )
        .get("area")
    )

    safe_value = ee.Number(
        ee.Algorithms.If(
            value,
            value,
            0,
        )
    )

    return float(
        safe_value.getInfo()
    )


def analyze_location(
    name,
    latitude,
    longitude,
):
    """
    Run final temporal-consensus experiment for one place.
    """

    area = (
        ee.Geometry.Point(
            [
                longitude,
                latitude,
            ]
        )
        .buffer(
            RADIUS_KM * 1000
        )
    )

    before_collection = (
        build_collection(
            area,
            BEFORE_DATE,
        )
    )

    after_collection = (
        build_collection(
            area,
            AFTER_DATE,
        )
    )

    before_count = int(
        before_collection
        .size()
        .getInfo()
    )

    after_count = int(
        after_collection
        .size()
        .getInfo()
    )

    if (
        before_count == 0
        or after_count == 0
    ):
        raise RuntimeError(
            "No Dynamic World observations."
        )

    before = build_consensus(
        before_collection
    )

    after = build_consensus(
        after_collection
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
    # AREAS
    # ------------------------------------------------------

    total_area_km2 = float(
        area
        .area()
        .divide(1e6)
        .getInfo()
    )

    comparable_area_km2 = (
        calculate_area_km2(
            comparable,
            area,
        )
    )

    coverage_percent = (
        comparable_area_km2
        / total_area_km2
        * 100
    )

    vegetation_to_built_km2 = (
        calculate_area_km2(
            vegetation_to_built,
            area,
        )
    )

    built_to_vegetation_km2 = (
        calculate_area_km2(
            built_to_vegetation,
            area,
        )
    )

    bare_to_built_km2 = (
        calculate_area_km2(
            bare_to_built,
            area,
        )
    )

    water_to_nonwater_km2 = (
        calculate_area_km2(
            water_to_nonwater,
            area,
        )
    )

    nonwater_to_water_km2 = (
        calculate_area_km2(
            nonwater_to_water,
            area,
        )
    )

    # ------------------------------------------------------
    # OUTPUT
    # ------------------------------------------------------

    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    print(
        "Observations:",
        before_count,
        "/",
        after_count,
    )

    print(
        "Comparable coverage:",
        f"{coverage_percent:.1f}%",
    )

    print(
        "Comparable area:",
        f"{comparable_area_km2:.2f} km2",
    )

    print(
        "Vegetation -> Built:",
        f"{vegetation_to_built_km2:.4f} km2",
    )

    print(
        "Built -> Vegetation:",
        f"{built_to_vegetation_km2:.4f} km2",
    )

    print(
        "Bare -> Built:",
        f"{bare_to_built_km2:.4f} km2",
    )

    print(
        "Water -> Non-water:",
        f"{water_to_nonwater_km2:.4f} km2",
    )

    print(
        "Non-water -> Water:",
        f"{nonwater_to_water_km2:.4f} km2",
    )


def main():
    """
    Run the experiment across all validation environments.
    """

    print(
        "SetQuery AI final temporal-consensus experiment"
    )

    print(
        "Probability threshold:",
        PROBABILITY_THRESHOLD,
    )

    print(
        "Minimum confidence frequency:",
        MIN_CONFIDENCE_FREQUENCY,
    )

    print(
        "Minimum temporal consensus:",
        MIN_CONSENSUS,
    )

    print(
        "Minimum confident observations:",
        MIN_CONFIDENT_OBSERVATIONS,
    )

    geocoder = Nominatim(
        user_agent=(
            "setquery-ai-final-consensus-investigation"
        )
    )

    for index, location_name in enumerate(
        LOCATIONS
    ):
        try:
            print()
            print(
                f"Processing "
                f"{index + 1}/{len(LOCATIONS)}: "
                f"{location_name}"
            )

            location = (
                geocoder.geocode(
                    location_name,
                    timeout=10,
                )
            )

            if location is None:
                print(
                    "GEOCODING FAILED"
                )
                continue

            analyze_location(
                location_name,
                location.latitude,
                location.longitude,
            )

        except Exception as error:
            print()
            print(
                location_name,
                "FAILED:",
                f"{type(error).__name__}: "
                f"{error}",
            )

        if (
            index
            < len(LOCATIONS) - 1
        ):
            time.sleep(
                1.2
            )


if __name__ == "__main__":
    main()