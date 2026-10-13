import ee

from .config import *

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

