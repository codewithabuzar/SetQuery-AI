import os
import json

from dotenv import load_dotenv
from google import genai


# Load secrets from .env
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")


if API_KEY:
    client = genai.Client(
        api_key=API_KEY
    )
else:
    client = None


def ask_gemini(
    question,
    result,
    location,
    before_date,
    after_date,
):
    """
    Answer questions about a SetQuery AI analysis
    using Gemini and only the supplied measurements.
    """

    if client is None:

        raise RuntimeError(
            "Gemini API key was not found."
        )


    # =================================================
    # DATA GIVEN TO GEMINI
    # =================================================

    context = {

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


    # =================================================
    # GROUNDED PROMPT
    # =================================================

    prompt = f"""
You are SetQuery AI, an assistant that explains
satellite-derived land-cover change analysis.

You have NOT personally inspected the satellite imagery.
You must reason only from the structured measurements
provided below.

ANALYSIS DATA:

{json.dumps(context, indent=2)}

USER QUESTION:

{question}


STRICT RULES:

1. Use only the supplied analysis data.

2. Never invent a detected building, road, forest,
   flood, fire, construction project, disaster or
   geographic event.

3. Do not claim that you directly inspected the
   satellite images.

4. Distinguish between:
   - net land-cover difference
   - explicit detected land-cover transitions.

5. Comparable coverage is NOT an accuracy percentage.

6. Coverage means the percentage of the requested
   region where classifications met the 60% confidence
   threshold in BOTH periods.

7. If coverage is limited, clearly mention that this
   restricts interpretation.

8. These values are satellite-derived ML estimates,
   not surveyed ground truth.

9. Do not infer the cause of a change unless the data
   explicitly provides a cause.

10. If the supplied data cannot answer the question,
    say that it cannot be determined from this analysis.

11. Be concise and easy to understand.

12. When useful, quote relevant values in km².
"""


    # =================================================
    # GEMINI
    # =================================================

    response = client.models.generate_content(
      model="gemini-3.8-flash",
        contents=prompt,
    )


    if not response.text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )


    return response.text