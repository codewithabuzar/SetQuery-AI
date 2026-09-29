import json
import os
import random
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors


load_dotenv()


API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)


if API_KEY:
    client = genai.Client(
        api_key=API_KEY
    )
else:
    client = None


class LLMUnavailableError(Exception):
    """Temporary Gemini availability failure."""


class LLMConfigurationError(Exception):
    """Gemini configuration problem."""


def build_context(
    result,
    location,
    before_date,
    after_date,
):
    """
    Create the only analysis data Gemini is
    permitted to reason from.
    """

    return {

        "location":
            location,

        "before_date":
            before_date,

        "after_date":
            after_date,

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
    }


def build_prompt(
    question,
    context,
):
    """
    Build a grounded prompt.
    """

    return f"""
You are SetQuery AI.

SetQuery AI explains land-cover change measurements
derived from satellite data and an ML classification
pipeline.

You do NOT directly inspect the satellite imagery.

ANALYSIS DATA:

{json.dumps(context, indent=2)}

USER QUESTION:

{question}


STRICT RULES:

1. Use only ANALYSIS DATA.

2. Never invent detected buildings, roads,
   construction projects, floods, fires,
   deforestation events, disasters or causes.

3. Never claim that you personally inspected
   or interpreted the satellite images.

4. Clearly distinguish between:

   A) net class-area difference

   and

   B) explicitly detected class transitions.

5. coverage_percent is NOT accuracy.

6. coverage_percent means the percentage of the
   requested study region where both periods met
   the configured ML confidence threshold.

7. If coverage is limited, explicitly qualify
   conclusions that depend on complete-area coverage.

8. The measurements are satellite-derived ML
   estimates, not surveyed ground truth.

9. Do not infer WHY a change occurred.

10. If the supplied measurements cannot answer
    the question, explicitly say so.

11. Quote numerical values when they help answer
    the question.

12. Keep the response concise and understandable.
"""


def ask_gemini(
    question,
    result,
    location,
    before_date,
    after_date,
    max_attempts=3,
):
    """
    Ask Gemini a grounded question.

    Temporary 429/503 failures are retried.
    Other failures are returned to the caller.
    """

    if client is None:

        raise LLMConfigurationError(
            "GEMINI_API_KEY is not configured."
        )


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

            status = getattr(
                error,
                "code",
                None
            )

            if status is None:

                status = getattr(
                    error,
                    "status_code",
                    None
                )


            # Temporary failures
            if status in (429, 503):

                if attempt < max_attempts:

                    delay = (
                        1.5
                        * (2 ** (attempt - 1))
                        + random.uniform(0, 0.5)
                    )

                    time.sleep(delay)

                    continue


                raise LLMUnavailableError(
                    f"Gemini temporarily unavailable "
                    f"after {max_attempts} attempts."
                ) from error


            raise


        except (
            TimeoutError,
            ConnectionError,
        ) as error:

            last_error = error

            if attempt < max_attempts:

                delay = (
                    1.5
                    * (2 ** (attempt - 1))
                )

                time.sleep(delay)

                continue


            raise LLMUnavailableError(
                "Gemini request failed because of "
                "a temporary network problem."
            ) from error


    raise LLMUnavailableError(
        "Gemini is currently unavailable."
    ) from last_error