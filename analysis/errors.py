class AnalysisValidationError(ValueError):
    """Raised when an analysis request is invalid."""


class AnalysisDataError(RuntimeError):
    """Raised when required Earth Engine data is unavailable."""
