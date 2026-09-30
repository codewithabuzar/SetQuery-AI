import json
import time

from geopy.geocoders import Nominatim

from analysis import (
    analyze_area,
    get_satellite_images,
    get_change_map,
)


BEFORE_DATE = "2022-09-15"
AFTER_DATE = "2025-09-15"

RADIUS_KM = 5
CONFIDENCE_THRESHOLD = 0.60


LOCATIONS = [
    "New Delhi, India",
    "Mumbai, Maharashtra, India",
    "Ludhiana, Punjab, India",
    "Dehradun, Uttarakhand, India",
    "Bhopal, Madhya Pradesh, India",
]


def main():
    geocoder = Nominatim(
        user_agent="setquery-ai-validation"
    )

    validation_results = []

    for index, location_name in enumerate(
        LOCATIONS,
        start=1,
    ):
        print()
        print("=" * 60)
        print(
            f"[{index}/{len(LOCATIONS)}] "
            f"{location_name}"
        )
        print("=" * 60)

        record = {
            "requested_location":
                location_name,

            "before_date":
                BEFORE_DATE,

            "after_date":
                AFTER_DATE,

            "radius_km":
                RADIUS_KM,

            "confidence_threshold":
                CONFIDENCE_THRESHOLD,
        }

        try:
            print("Geocoding...")

            location = geocoder.geocode(
                location_name,
                timeout=10,
            )

            if location is None:
                raise RuntimeError(
                    "Location could not be geocoded."
                )

            latitude = location.latitude
            longitude = location.longitude

            record["resolved_location"] = (
                location.address
            )

            record["latitude"] = latitude
            record["longitude"] = longitude

            print(
                f"Resolved: {location.address}"
            )

            print(
                "Running Dynamic World analysis..."
            )

            result = analyze_area(
                latitude=latitude,
                longitude=longitude,
                before_date=BEFORE_DATE,
                after_date=AFTER_DATE,
                radius_km=RADIUS_KM,
                confidence_threshold=(
                    CONFIDENCE_THRESHOLD
                ),
            )

            print(
                "Checking Sentinel-2 imagery..."
            )

            images = get_satellite_images(
                latitude=latitude,
                longitude=longitude,
                before_date=BEFORE_DATE,
                after_date=AFTER_DATE,
                radius_km=RADIUS_KM,
            )

            print(
                "Checking change map..."
            )

            change_map = get_change_map(
                latitude=latitude,
                longitude=longitude,
                before_date=BEFORE_DATE,
                after_date=AFTER_DATE,
                radius_km=RADIUS_KM,
                confidence_threshold=(
                    CONFIDENCE_THRESHOLD
                ),
            )

            vegetation_change = (
                result[
                    "after_vegetation_km2"
                ]
                -
                result[
                    "before_vegetation_km2"
                ]
            )

            built_change = (
                result[
                    "after_built_km2"
                ]
                -
                result[
                    "before_built_km2"
                ]
            )

            water_change = (
                result[
                    "after_water_km2"
                ]
                -
                result[
                    "before_water_km2"
                ]
            )

            record.update(
                {
                    "status":
                        "success",

                    "total_area_km2":
                        result[
                            "total_area_km2"
                        ],

                    "comparable_area_km2":
                        result[
                            "comparable_area_km2"
                        ],

                    "coverage_percent":
                        result[
                            "coverage_percent"
                        ],

                    "dynamic_world_before":
                        result[
                            "before_observations"
                        ],

                    "dynamic_world_after":
                        result[
                            "after_observations"
                        ],

                    "sentinel_before":
                        images[
                            "before_sentinel_observations"
                        ],

                    "sentinel_after":
                        images[
                            "after_sentinel_observations"
                        ],

                    "before_vegetation_km2":
                        result[
                            "before_vegetation_km2"
                        ],

                    "after_vegetation_km2":
                        result[
                            "after_vegetation_km2"
                        ],

                    "vegetation_net_km2":
                        vegetation_change,

                    "before_built_km2":
                        result[
                            "before_built_km2"
                        ],

                    "after_built_km2":
                        result[
                            "after_built_km2"
                        ],

                    "built_net_km2":
                        built_change,

                    "before_water_km2":
                        result[
                            "before_water_km2"
                        ],

                    "after_water_km2":
                        result[
                            "after_water_km2"
                        ],

                    "water_net_km2":
                        water_change,

                    "vegetation_to_built_km2":
                        result[
                            "vegetation_to_built_km2"
                        ],

                    "built_to_vegetation_km2":
                        result[
                            "built_to_vegetation_km2"
                        ],

                    "bare_to_built_km2":
                        result[
                            "bare_to_built_km2"
                        ],

                    "water_to_nonwater_km2":
                        result[
                            "water_to_nonwater_km2"
                        ],

                    "nonwater_to_water_km2":
                        result[
                            "nonwater_to_water_km2"
                        ],

                    "before_image_generated":
                        bool(
                            images.get(
                                "before_url"
                            )
                        ),

                    "after_image_generated":
                        bool(
                            images.get(
                                "after_url"
                            )
                        ),

                    "change_map_generated":
                        bool(
                            change_map.get(
                                "change_url"
                            )
                        ),

                    "warnings":
                        result.get(
                            "warnings",
                            [],
                        ),
                }
            )

            print(
                "Coverage: "
                f"{record['coverage_percent']:.1f}%"
            )

            print(
                "Comparable area: "
                f"{record['comparable_area_km2']:.2f} km²"
            )

            print(
                "Vegetation net: "
                f"{vegetation_change:+.4f} km²"
            )

            print(
                "Built net: "
                f"{built_change:+.4f} km²"
            )

            print(
                "Water net: "
                f"{water_change:+.4f} km²"
            )

            print(
                "Visual products: OK"
            )

        except Exception as error:
            record["status"] = "failed"

            record["error"] = (
                f"{type(error).__name__}: "
                f"{error}"
            )

            print(
                "FAILED:"
            )

            print(
                record["error"]
            )

        validation_results.append(
            record
        )

        # Be polite to Nominatim and avoid rapidly
        # starting the next geocoding request.
        if index < len(LOCATIONS):
            time.sleep(1.2)

    output_file = (
        "modern_validation_results.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            validation_results,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)

    print(
        f"Results saved to: {output_file}"
    )

    print()

    for record in validation_results:
        if record["status"] == "success":
            print(
                f"{record['requested_location']}: "
                f"{record['coverage_percent']:.1f}% coverage"
            )
        else:
            print(
                f"{record['requested_location']}: FAILED"
            )


if __name__ == "__main__":
    main()