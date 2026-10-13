from datetime import date, datetime, timedelta

from .config import *
from .errors import AnalysisValidationError

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

