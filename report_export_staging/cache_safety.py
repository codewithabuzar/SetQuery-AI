"""Safe cache fingerprints for SetQuery PDF reports."""

import hashlib
import json
import math


def normalize(value):
    """Convert report inputs into stable JSON-compatible values."""

    if isinstance(value, dict):
        return {
            str(key): normalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }

    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]

    if isinstance(value, (str, int, bool)) or value is None:
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                "Non-finite values cannot be fingerprinted."
            )
        return value

    if hasattr(value, "isoformat"):
        return value.isoformat()

    raise TypeError(
        f"Unsupported cache fingerprint type: {type(value).__name__}"
    )


def fingerprint(value):
    """Create a deterministic SHA-256 fingerprint."""

    payload = json.dumps(
        normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def analysis_fingerprint(data):
    """Fingerprint comparison analysis and measured results."""

    return fingerprint({
        "mode": data["mode"],
        "location": data["location"],
        "latitude": data["latitude"],
        "longitude": data["longitude"],
        "before_date": data["before_date"],
        "after_date": data["after_date"],
        "radius_km": data["radius_km"],
        "result": data["result"],
    })


def trend_fingerprint(data):
    """Fingerprint Trend analysis and all observation periods."""

    return fingerprint({
        "location": data["location"],
        "latitude": data["latitude"],
        "longitude": data["longitude"],
        "radius_km": data["radius_km"],
        "periods": data["periods"],
        "methodology": data.get("methodology_note"),
        "warnings": data.get("warnings", []),
    })


def report_fingerprint(
    analysis_data,
    preset,
    selected,
    include_ai,
):
    """Fingerprint analysis and report configuration."""

    return fingerprint({
        "analysis": analysis_fingerprint(analysis_data),
        "preset": preset,
        "selected_evidence": sorted(selected),
        "include_ai": bool(include_ai),
    })


def evidence_matches(
    cached_analysis_fingerprint,
    current_analysis_fingerprint,
):
    """Only reuse evidence with explicitly matching provenance."""

    return (
        cached_analysis_fingerprint is not None
        and cached_analysis_fingerprint
        == current_analysis_fingerprint
    )
