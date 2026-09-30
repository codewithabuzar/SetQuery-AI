import json
import time

from geopy.geocoders import Nominatim

from historical_analysis import (
    analyze_historical_area,
    get_historical_satellite_images,
)


BEFORE_DATE = "2012-09-15"
AFTER_DATE = "2025-09-15"

RADIUS_KM = 5


LOCATIONS = [
    "New Delhi, India",
    "Mumbai, Maharashtra, India",
    "Ludhiana, Punjab, India",
    "Dehradun, Uttarakhand, India",
    "Bhopal, Madhya Pradesh, India",
]


def sensor_names(sensor_list):
    """
    Build a compact sensor summary.
    """

    return [
        {
            "name":
                sensor["name"],

            "sensor":
                sensor["sensor"],

            "observations":
                sensor["observations"],
        }
        for sensor in sensor_list
    ]


def sensor_text(sensor_list):
    """
    Build readable terminal sensor text.
    """

    return ", ".join(
        (
            f"{sensor['name']} "
            f"({sensor['observations']})"
        )
        for sensor in sensor_list
    )


def main():
    """
    Run Historical Spectral sanity checks across
    several different environments.

    These results are NOT ground-truth validation.
    """

    geocoder = Nominatim(
        user_agent=(
            "setquery-ai-historical-validation"
        )
    )

    validation_results = []

    print()
    print("=" * 60)
    print("SETQUERY AI HISTORICAL VALIDATION")
    print("=" * 60)

    print(
        f"Before target: {BEFORE_DATE}"
    )

    print(
        f"After target:  {AFTER_DATE}"
    )

    print(
        f"Radius:        {RADIUS_KM} km"
    )

    print()

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
        }

        try:
            print(
                "Geocoding..."
            )

            location = geocoder.geocode(
                location_name,
                timeout=10,
            )

            if location is None:

                raise RuntimeError(
                    "Location could not be geocoded."
                )

            latitude = (
                location.latitude
            )

            longitude = (
                location.longitude
            )

            record[
                "resolved_location"
            ] = location.address

            record[
                "latitude"
            ] = latitude

            record[
                "longitude"
            ] = longitude

            print(
                f"Resolved: {location.address}"
            )

            print(
                "Running historical spectral analysis..."
            )

            result = (
                analyze_historical_area(
                    latitude=latitude,
                    longitude=longitude,
                    before_date=BEFORE_DATE,
                    after_date=AFTER_DATE,
                    radius_km=RADIUS_KM,
                )
            )

            print(
                "Generating Landsat imagery..."
            )

            images = (
                get_historical_satellite_images(
                    latitude=latitude,
                    longitude=longitude,
                    before_date=BEFORE_DATE,
                    after_date=AFTER_DATE,
                    radius_km=RADIUS_KM,
                )
            )

            record.update(
                {
                    "status":
                        "success",

                    "analysis_mode":
                        result[
                            "analysis_mode"
                        ],

                    "method":
                        result[
                            "method"
                        ],

                    "approximate_resolution_m":
                        result[
                            "approximate_resolution_m"
                        ],

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

                    "before_sensors":
                        sensor_names(
                            result[
                                "before_sensors"
                            ]
                        ),

                    "after_sensors":
                        sensor_names(
                            result[
                                "after_sensors"
                            ]
                        ),

                    "before_observations":
                        images[
                            "before_observations"
                        ],

                    "after_observations":
                        images[
                            "after_observations"
                        ],

                    "before_mean_ndvi":
                        result[
                            "before_mean_ndvi"
                        ],

                    "after_mean_ndvi":
                        result[
                            "after_mean_ndvi"
                        ],

                    "ndvi_change":
                        result[
                            "ndvi_change"
                        ],

                    "before_mean_mndwi":
                        result[
                            "before_mean_mndwi"
                        ],

                    "after_mean_mndwi":
                        result[
                            "after_mean_mndwi"
                        ],

                    "mndwi_change":
                        result[
                            "mndwi_change"
                        ],

                    "before_mean_ndbi":
                        result[
                            "before_mean_ndbi"
                        ],

                    "after_mean_ndbi":
                        result[
                            "after_mean_ndbi"
                        ],

                    "ndbi_change":
                        result[
                            "ndbi_change"
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

                    "warnings":
                        result.get(
                            "warnings",
                            [],
                        ),
                }
            )

            print(
                "Before sensors:",
                sensor_text(
                    result[
                        "before_sensors"
                    ]
                ),
            )

            print(
                "After sensors:",
                sensor_text(
                    result[
                        "after_sensors"
                    ]
                ),
            )

            print(
                "Coverage:",
                (
                    f"{result['coverage_percent']:.1f}%"
                ),
            )

            print(
                "Comparable area:",
                (
                    f"{result['comparable_area_km2']:.2f} km²"
                ),
            )

            print(
                "NDVI:",
                (
                    f"{result['before_mean_ndvi']:.3f}"
                    " -> "
                    f"{result['after_mean_ndvi']:.3f}"
                    " | Δ "
                    f"{result['ndvi_change']:+.3f}"
                ),
            )

            print(
                "MNDWI:",
                (
                    f"{result['before_mean_mndwi']:.3f}"
                    " -> "
                    f"{result['after_mean_mndwi']:.3f}"
                    " | Δ "
                    f"{result['mndwi_change']:+.3f}"
                ),
            )

            print(
                "NDBI:",
                (
                    f"{result['before_mean_ndbi']:.3f}"
                    " -> "
                    f"{result['after_mean_ndbi']:.3f}"
                    " | Δ "
                    f"{result['ndbi_change']:+.3f}"
                ),
            )

            print(
                "Before image:",
                (
                    "OK"
                    if record[
                        "before_image_generated"
                    ]
                    else "FAILED"
                ),
            )

            print(
                "After image:",
                (
                    "OK"
                    if record[
                        "after_image_generated"
                    ]
                    else "FAILED"
                ),
            )

            if record[
                "warnings"
            ]:

                print(
                    "Warnings:"
                )

                for warning in record[
                    "warnings"
                ]:

                    print(
                        f" - {warning}"
                    )

        except Exception as error:

            record[
                "status"
            ] = "failed"

            record[
                "error"
            ] = (
                f"{type(error).__name__}: "
                f"{error}"
            )

            print(
                "FAILED:"
            )

            print(
                record[
                    "error"
                ]
            )

        validation_results.append(
            record
        )

        if (
            index
            < len(LOCATIONS)
        ):

            time.sleep(
                1.2
            )

    output_file = (
        "historical_validation_results.json"
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
    print("HISTORICAL VALIDATION COMPLETE")
    print("=" * 60)

    print(
        f"Results saved to: {output_file}"
    )

    print()

    for record in validation_results:

        if (
            record[
                "status"
            ]
            == "success"
        ):

            print(
                f"{record['requested_location']}: "
                f"{record['coverage_percent']:.1f}% coverage, "
                f"NDVI Δ {record['ndvi_change']:+.3f}, "
                f"MNDWI Δ {record['mndwi_change']:+.3f}, "
                f"NDBI Δ {record['ndbi_change']:+.3f}"
            )

        else:

            print(
                f"{record['requested_location']}: FAILED"
            )


if __name__ == "__main__":
    main()