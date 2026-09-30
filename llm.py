import json
import os
import random
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors


# ==========================================================
# CONFIGURATION
# ==========================================================

load_dotenv()

API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)


if API_KEY:
    client = genai.Client(
        api_key=API_KEY
    )
else:
    client = None


# ==========================================================
# ERRORS
# ==========================================================

class LLMUnavailableError(Exception):
    """Gemini is temporarily unavailable."""


class LLMConfigurationError(Exception):
    """Gemini configuration problem."""


# ==========================================================
# MODERN ML CONTEXT
# ==========================================================

def build_context(
    result,
    location,
    before_date,
    after_date,
):
    """
    Build the grounded context for Modern ML mode.

    This context represents the Sentinel-2 +
    Dynamic World analysis only.
    """

    return {
        "analysis_mode":
            "modern_ml",

        "method":
            "Sentinel-2 + Dynamic World ML",

        "location":
            location,

        "before_target_date":
            str(before_date),

        "after_target_date":
            str(after_date),

        "confidence_threshold":
            0.60,

        "before_observations":
            result["before_observations"],

        "after_observations":
            result["after_observations"],

        "total_area_km2":
            result["total_area_km2"],

        "comparable_area_km2":
            result["comparable_area_km2"],

        "coverage_percent":
            result["coverage_percent"],

        "before_vegetation_km2":
            result["before_vegetation_km2"],

        "after_vegetation_km2":
            result["after_vegetation_km2"],

        "before_built_km2":
            result["before_built_km2"],

        "after_built_km2":
            result["after_built_km2"],

        "before_water_km2":
            result["before_water_km2"],

        "after_water_km2":
            result["after_water_km2"],

        "before_bare_km2":
            result["before_bare_km2"],

        "after_bare_km2":
            result["after_bare_km2"],

        "vegetation_to_built_km2":
            result["vegetation_to_built_km2"],

        "built_to_vegetation_km2":
            result["built_to_vegetation_km2"],

        "bare_to_built_km2":
            result["bare_to_built_km2"],

        "water_to_nonwater_km2":
            result["water_to_nonwater_km2"],

        "nonwater_to_water_km2":
            result["nonwater_to_water_km2"],

        "warnings":
            result.get(
                "warnings",
                [],
            ),
    }


def build_prompt(
    question,
    context,
):
    """
    Build the grounded Modern ML prompt.
    """

    return f"""
You are SetQuery AI.

You explain measurements produced by SetQuery AI's
Modern ML analysis mode.

This mode uses Sentinel-2 satellite imagery and
Google Dynamic World machine-learning land-cover data.

You do NOT directly inspect satellite imagery.

ANALYSIS DATA:

{json.dumps(context, indent=2)}

USER QUESTION:

{question}

STRICT RULES:

1. Use only ANALYSIS DATA.

2. Never invent buildings, roads, construction projects,
   floods, fires, deforestation events, disasters, people,
   infrastructure projects, or causes.

3. Never claim that you visually inspected or interpreted
   the satellite imagery.

4. The target dates are comparison targets around which
   composites are constructed. Do not claim that imagery
   was captured exactly on those dates.

5. Clearly distinguish between:
   A) net class-area difference
   and
   B) explicitly measured class transitions.

6. coverage_percent is NOT accuracy.

7. coverage_percent is the portion of the requested study
   region where both periods met the configured Dynamic
   World ML confidence requirement.

8. If comparable coverage is low, conclusions must be
   limited to the comparable subset.

9. If coverage is below 20%, explicitly state that broad
   area-level conclusions are not supported.

10. The measurements are satellite-derived ML estimates,
    not surveyed ground truth.

11. Do not infer WHY a measured change occurred.

12. Do not claim reliable detection of individual houses,
    individual trees, tiny roads, or exact property-level
    changes.

13. If ANALYSIS DATA cannot answer the question, say so.

14. Quote relevant numerical values when useful.

15. Keep the answer concise and understandable.
"""


# ==========================================================
# HISTORICAL SPECTRAL CONTEXT
# ==========================================================

def _safe_sensor_context(
    sensor_list,
):
    """
    Convert historical sensor metadata into a compact
    JSON-safe representation.
    """

    sensors = []

    for item in sensor_list:

        sensors.append(
            {
                "name":
                    item.get("name"),

                "sensor":
                    item.get("sensor"),

                "observations":
                    item.get("observations"),
            }
        )

    return sensors


def build_historical_context(
    result,
    location,
    before_date,
    after_date,
):
    """
    Build a grounded context for Historical Spectral mode.

    Historical mode uses Landsat spectral indices and does
    not provide Dynamic World categorical land-cover areas.
    """

    return {
        "analysis_mode":
            "historical_spectral",

        "method":
            result.get(
                "method",
                "Cloud-masked Landsat spectral comparison",
            ),

        "location":
            location,

        "before_target_date":
            str(before_date),

        "after_target_date":
            str(after_date),

        "approximate_resolution_m":
            result.get(
                "approximate_resolution_m",
                30,
            ),

        "total_area_km2":
            result["total_area_km2"],

        "comparable_area_km2":
            result["comparable_area_km2"],

        "coverage_percent":
            result["coverage_percent"],

        "before_mean_ndvi":
            result["before_mean_ndvi"],

        "after_mean_ndvi":
            result["after_mean_ndvi"],

        "ndvi_change":
            result["ndvi_change"],

        "before_mean_mndwi":
            result["before_mean_mndwi"],

        "after_mean_mndwi":
            result["after_mean_mndwi"],

        "mndwi_change":
            result["mndwi_change"],

        "before_mean_ndbi":
            result["before_mean_ndbi"],

        "after_mean_ndbi":
            result["after_mean_ndbi"],

        "ndbi_change":
            result["ndbi_change"],

        "before_sensors":
            _safe_sensor_context(
                result.get(
                    "before_sensors",
                    [],
                )
            ),

        "after_sensors":
            _safe_sensor_context(
                result.get(
                    "after_sensors",
                    [],
                )
            ),

        "before_window":
            result.get(
                "before_window"
            ),

        "after_window":
            result.get(
                "after_window"
            ),

        "warnings":
            result.get(
                "warnings",
                [],
            ),
    }


def build_historical_prompt(
    question,
    context,
):
    """
    Build the grounded Historical Spectral prompt.
    """

    return f"""
You are SetQuery AI.

You are explaining measurements produced by SetQuery AI's
Historical Spectral analysis mode.

This mode uses cloud-masked Landsat composites and spectral
indices. It is NOT a Dynamic World categorical land-cover
classification.

You do NOT directly inspect satellite imagery.

ANALYSIS DATA:

{json.dumps(context, indent=2)}

USER QUESTION:

{question}

SPECTRAL INDEX MEANINGS:

NDVI:
A vegetation-related spectral indicator.

MNDWI:
A water-related spectral indicator.

NDBI:
A built/bare-related spectral indicator.

STRICT RULES:

1. Use only ANALYSIS DATA.

2. Never invent buildings, roads, construction projects,
   floods, fires, deforestation events, disasters, people,
   infrastructure projects, or causes.

3. Never claim that you visually inspected the imagery.

4. Do NOT translate NDVI into vegetation area in km².

5. Do NOT translate MNDWI into water area in km².

6. Do NOT translate NDBI into built-up or urban area in km².

7. Do NOT claim that an increase in NDBI proves
   urbanization or construction.

8. Do NOT claim that a decrease in NDBI proves that
   buildings disappeared.

9. NDBI can respond to both built and bare surfaces.

10. An NDVI change describes a vegetation-related spectral
    signal, not a direct categorical vegetation transition.

11. An MNDWI change describes a water-related spectral
    signal, not a direct flood, lake, or water-area
    measurement.

12. coverage_percent is NOT accuracy. It is the percentage
    of the requested region containing valid comparable
    Landsat pixels in both periods.

13. If coverage is below 20%, explicitly state that broad
    area-level conclusions are not supported.

14. Different Landsat sensor generations may be used in
    the two periods. Their spectral bandpass differences
    can influence absolute index values.

15. The target dates are centers of composite windows.
    Do not claim the images were captured exactly on the
    target dates.

16. Do not infer WHY a spectral difference occurred.

17. These are satellite-derived spectral measurements,
    not surveyed ground truth.

18. Landsat resolution in this workflow is approximately
    30 metres. Do not claim individual-building,
    individual-tree, tiny-road, or property-level change.

19. If the supplied measurements cannot answer the user's
    question, explicitly say so.

20. Quote relevant measurements when useful and keep the
    response concise and understandable.
"""


# ==========================================================
# SHARED GEMINI REQUEST HANDLING
# ==========================================================

def _get_status_code(error):
    """
    Extract an HTTP/API status code where possible.
    """

    status = getattr(
        error,
        "code",
        None,
    )

    if status is None:

        status = getattr(
            error,
            "status_code",
            None,
        )

    try:
        return int(status)

    except (
        TypeError,
        ValueError,
    ):
        return status


def _generate_grounded_response(
    prompt,
    max_attempts=3,
):
    """
    Send a grounded prompt to Gemini.

    429:
        fail immediately to deterministic fallback.

    503:
        perform controlled retries.

    Network failures:
        perform controlled retries.
    """

    if client is None:

        raise LLMConfigurationError(
            "GEMINI_API_KEY is not configured."
        )

    last_error = None

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        try:

            response = (
                client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                )
            )

            text = response.text

            if not text:

                raise LLMUnavailableError(
                    "Gemini returned an empty response."
                )

            return text.strip()

        except errors.APIError as error:

            last_error = error

            status = (
                _get_status_code(
                    error
                )
            )

            # Quota / rate limit:
            # do not immediately waste more requests.
            if status == 429:

                raise LLMUnavailableError(
                    "Gemini quota or rate limit reached. "
                    "Using the local grounded fallback."
                ) from error

            # Temporary service/capacity problem.
            if status == 503:

                if attempt < max_attempts:

                    delay = (
                        1.5
                        * (
                            2
                            ** (
                                attempt - 1
                            )
                        )
                        + random.uniform(
                            0,
                            0.5,
                        )
                    )

                    time.sleep(
                        delay
                    )

                    continue

                raise LLMUnavailableError(
                    "Gemini service remained temporarily "
                    f"unavailable after "
                    f"{max_attempts} attempts."
                ) from error

            # Unexpected API errors are not silently
            # mislabeled as quota/capacity failures.
            raise

        except (
            TimeoutError,
            ConnectionError,
            ConnectionResetError,
        ) as error:

            last_error = error

            if attempt < max_attempts:

                delay = (
                    1.5
                    * (
                        2
                        ** (
                            attempt - 1
                        )
                    )
                )

                time.sleep(
                    delay
                )

                continue

            raise LLMUnavailableError(
                "Gemini request failed after "
                f"{max_attempts} attempts because "
                "of a temporary network problem: "
                f"{type(error).__name__}."
            ) from error

    raise LLMUnavailableError(
        "Gemini is currently unavailable."
    ) from last_error


# ==========================================================
# PUBLIC MODERN ML GEMINI FUNCTION
# ==========================================================

def ask_gemini(
    question,
    result,
    location,
    before_date,
    after_date,
    max_attempts=3,
):
    """
    Ask Gemini about a Modern ML analysis.
    """

    context = build_context(
        result=result,
        location=location,
        before_date=before_date,
        after_date=after_date,
    )

    prompt = build_prompt(
        question=question,
        context=context,
    )

    return _generate_grounded_response(
        prompt=prompt,
        max_attempts=max_attempts,
    )


# ==========================================================
# PUBLIC HISTORICAL GEMINI FUNCTION
# ==========================================================

def ask_gemini_historical(
    question,
    result,
    location,
    before_date,
    after_date,
    max_attempts=3,
):
    """
    Ask Gemini about a Historical Spectral analysis.

    This uses a separate schema and prompt so Landsat
    spectral indicators cannot be silently treated as
    Dynamic World categorical areas.
    """

    context = (
        build_historical_context(
            result=result,
            location=location,
            before_date=before_date,
            after_date=after_date,
        )
    )

    prompt = (
        build_historical_prompt(
            question=question,
            context=context,
        )
    )

    return _generate_grounded_response(
        prompt=prompt,
        max_attempts=max_attempts,
    )