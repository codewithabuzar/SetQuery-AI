"""Verified supplementary evidence cache for SetQuery reports."""

from .cache_safety import analysis_fingerprint, fingerprint


EVIDENCE_CACHE_VERSION = "setquery-evidence-v1"

EVIDENCE_TYPES = (
    "burn",
    "vegetation",
    "flood",
)


def evidence_cache_key(analysis_data, evidence_type):
    """Build a provenance-aware evidence cache key."""

    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(
            f"Unsupported evidence type: {evidence_type}"
        )

    return fingerprint({
        "version": EVIDENCE_CACHE_VERSION,
        "analysis": analysis_fingerprint(analysis_data),
        "type": evidence_type,
    })


def get_cached_evidence(cache, analysis_data, evidence_type):
    """Return evidence only when its exact cache key matches."""

    if not isinstance(cache, dict):
        return None

    key = evidence_cache_key(
        analysis_data,
        evidence_type,
    )

    return cache.get(key)


def store_cached_evidence(
    cache,
    analysis_data,
    evidence_type,
    result,
):
    """Store evidence with a verified analysis fingerprint."""

    if not isinstance(cache, dict):
        raise TypeError("Evidence cache must be a dictionary.")

    key = evidence_cache_key(
        analysis_data,
        evidence_type,
    )

    cache[key] = result

    return key
