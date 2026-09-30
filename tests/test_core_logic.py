from analysis_router import choose_analysis_mode

from report import (
    get_coverage_interpretation,
    generate_analysis_summary,
)

from historical_report import (
    get_historical_coverage_level,
    get_historical_observation_support,
    get_historical_source_support,
    answer_historical_query,
)


# ==========================================================
# MODE ROUTING
# ==========================================================

def test_2012_routes_to_historical():
    assert (
        choose_analysis_mode(
            "2012-09-15",
            "2025-09-15",
        )
        == "historical_spectral"
    )


def test_2016_routes_to_historical():
    assert (
        choose_analysis_mode(
            "2016-09-15",
            "2025-09-15",
        )
        == "historical_spectral"
    )


def test_2018_routes_to_modern():
    assert (
        choose_analysis_mode(
            "2018-09-15",
            "2025-09-15",
        )
        == "modern_ml"
    )


def test_2022_routes_to_modern():
    assert (
        choose_analysis_mode(
            "2022-09-15",
            "2025-09-15",
        )
        == "modern_ml"
    )


# ==========================================================
# MODERN COVERAGE INTERPRETATION
# ==========================================================

def test_modern_good_coverage():
    result = get_coverage_interpretation(
        75
    )

    assert result["level"] == "GOOD"


def test_modern_moderate_coverage():
    result = get_coverage_interpretation(
        50
    )

    assert result["level"] == "MODERATE"


def test_modern_limited_coverage():
    result = get_coverage_interpretation(
        30
    )

    assert result["level"] == "LIMITED"


def test_modern_very_low_coverage():
    result = get_coverage_interpretation(
        10
    )

    assert result["level"] == "VERY LOW"


def test_modern_coverage_boundaries():
    assert (
        get_coverage_interpretation(
            70
        )["level"]
        == "GOOD"
    )

    assert (
        get_coverage_interpretation(
            40
        )["level"]
        == "MODERATE"
    )

    assert (
        get_coverage_interpretation(
            20
        )["level"]
        == "LIMITED"
    )

    assert (
        get_coverage_interpretation(
            19.9
        )["level"]
        == "VERY LOW"
    )


# ==========================================================
# HISTORICAL COVERAGE INTERPRETATION
# ==========================================================

def test_historical_coverage_levels():
    assert (
        get_historical_coverage_level(
            80
        )
        == "GOOD"
    )

    assert (
        get_historical_coverage_level(
            50
        )
        == "MODERATE"
    )

    assert (
        get_historical_coverage_level(
            25
        )
        == "LIMITED"
    )

    assert (
        get_historical_coverage_level(
            10
        )
        == "VERY LOW"
    )


# ==========================================================
# HISTORICAL OBSERVATION SUPPORT
# ==========================================================

def test_historical_observation_support():
    assert (
        get_historical_observation_support(
            7
        )
        == "GOOD"
    )

    assert (
        get_historical_observation_support(
            5
        )
        == "GOOD"
    )

    assert (
        get_historical_observation_support(
            4
        )
        == "MODERATE"
    )

    assert (
        get_historical_observation_support(
            3
        )
        == "MODERATE"
    )

    assert (
        get_historical_observation_support(
            2
        )
        == "LIMITED"
    )

    assert (
        get_historical_observation_support(
            1
        )
        == "VERY LOW"
    )


def test_historical_source_support_counts_sensors():
    result = {
        "before_sensors": [
            {
                "name": "Landsat 7",
                "observations": 1,
            }
        ],

        "after_sensors": [
            {
                "name": "Landsat 8",
                "observations": 2,
            },
            {
                "name": "Landsat 9",
                "observations": 5,
            },
        ],
    }

    support = (
        get_historical_source_support(
            result
        )
    )

    assert support[
        "before_count"
    ] == 1

    assert support[
        "before_level"
    ] == "VERY LOW"

    assert support[
        "after_count"
    ] == 7

    assert support[
        "after_level"
    ] == "GOOD"


# ==========================================================
# HISTORICAL GROUNDED Q&A
# ==========================================================

def historical_result():
    return {
        "coverage_percent":
            57.8,

        "comparable_area_km2":
            44.87,

        "before_mean_ndvi":
            0.300,

        "after_mean_ndvi":
            0.378,

        "ndvi_change":
            0.078,

        "before_mean_mndwi":
            -0.250,

        "after_mean_mndwi":
            -0.262,

        "mndwi_change":
            -0.012,

        "before_mean_ndbi":
            -0.070,

        "after_mean_ndbi":
            -0.111,

        "ndbi_change":
            -0.041,

        "before_sensors": [
            {
                "name": "Landsat 7",
                "observations": 1,
            }
        ],

        "after_sensors": [
            {
                "name": "Landsat 8",
                "observations": 2,
            },
            {
                "name": "Landsat 9",
                "observations": 5,
            },
        ],
    }


def test_historical_built_query_is_conservative():
    answer = (
        answer_historical_query(
            "Did built-up area increase?",
            historical_result(),
        )
    ).lower()

    assert "ndbi" in answer

    assert (
        "cannot by itself"
        in answer
    )

    assert (
        "built-up area"
        in answer
    )


def test_historical_water_query_is_conservative():
    answer = (
        answer_historical_query(
            "How did water change?",
            historical_result(),
        )
    ).lower()

    assert "mndwi" in answer

    assert (
        "not a direct measurement"
        in answer
    )


def test_historical_vegetation_query_is_conservative():
    answer = (
        answer_historical_query(
            "How did vegetation change?",
            historical_result(),
        )
    ).lower()

    assert "ndvi" in answer

    assert (
        "not be interpreted"
        in answer
    )


# ==========================================================
# MODERN SUMMARY GROUNDING
# ==========================================================

def modern_result(
    coverage=10.0,
):
    return {
        "before_observations":
            10,

        "after_observations":
            10,

        "total_area_km2":
            77.60,

        "comparable_area_km2":
            7.76,

        "coverage_percent":
            coverage,

        "before_vegetation_km2":
            3.00,

        "after_vegetation_km2":
            2.95,

        "before_built_km2":
            4.00,

        "after_built_km2":
            4.05,

        "before_water_km2":
            0.20,

        "after_water_km2":
            0.20,

        "before_bare_km2":
            0.10,

        "after_bare_km2":
            0.10,

        "vegetation_to_built_km2":
            0.05,

        "built_to_vegetation_km2":
            0.00,

        "bare_to_built_km2":
            0.00,

        "water_to_nonwater_km2":
            0.00,

        "nonwater_to_water_km2":
            0.00,

        "classification_method":
            "dynamic_world_temporal_consensus",

        "confidence_threshold":
            0.60,

        "min_confident_observations":
            2,

        "min_confidence_frequency":
            0.50,

        "min_temporal_consensus":
            0.60,
    }


def test_low_coverage_summary_blocks_broad_conclusions():
    summary = (
        generate_analysis_summary(
            location="Test City",
            before_date="2022-09-15",
            after_date="2025-09-15",
            result=modern_result(
                coverage=10.0
            ),
        )
    ).lower()

    assert "very low" in summary

    assert (
        "broad area-level conclusions"
        in summary
    )


def test_summary_explains_coverage_not_accuracy():
    summary = (
        generate_analysis_summary(
            location="Test City",
            before_date="2022-09-15",
            after_date="2025-09-15",
            result=modern_result(
                coverage=55.0
            ),
        )
    ).lower()

    assert (
        "not an accuracy"
        in summary
    )

    assert (
        "temporal-consensus"
        in summary
    )


def test_summary_contains_temporal_consensus_rules():
    summary = (
        generate_analysis_summary(
            location="Test City",
            before_date="2022-09-15",
            after_date="2025-09-15",
            result=modern_result(
                coverage=55.0
            ),
        )
    ).lower()

    assert "60%" in summary

    assert (
        "2 confident observations"
        in summary
    )

    assert (
        "50%"
        in summary
    )

    assert (
        "dominant class"
        in summary
    )