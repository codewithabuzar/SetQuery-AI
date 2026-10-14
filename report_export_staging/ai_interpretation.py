"""Optional grounded AI interpretation for SetQuery PDF reports."""

from llm import (
    ask_gemini,
    ask_gemini_historical,
)

from report import generate_analysis_summary
from historical_report import generate_historical_summary


REPORT_QUESTION = (
    "Provide a concise professional interpretation of the "
    "measured satellite analysis. Summarize the most relevant "
    "changes, comparable coverage, uncertainty and limitations. "
    "Do not invent causes, disasters, structures or observations. "
    "Do not add unrelated notes about the developer or application."
)


def generate_report_interpretation(
    analysis_data,
    enabled=False,
    progress=None,
):
    """
    Generate optional AI explanation.

    When disabled, no Gemini request is made.

    Always returns an interpretation and its source.
    """

    if not enabled:
        return None

    def notify(message):
        if progress is not None:
            progress(message)

    mode = analysis_data["mode"]
    result = analysis_data["result"]

    kwargs = {
        "question": REPORT_QUESTION,
        "result": result,
        "location": analysis_data["location"],
        "before_date": analysis_data["before_date"],
        "after_date": analysis_data["after_date"],
        "max_attempts": 1,
    }

    notify("Generating optional AI interpretation...")

    try:
        if mode == "modern_ml":
            text = ask_gemini(**kwargs)
        else:
            text = ask_gemini_historical(**kwargs)

        return {
            "source": "gemini",
            "text": text,
        }

    except Exception:

        notify(
            "AI unavailable; preparing deterministic "
            "analysis interpretation..."
        )

        if mode == "modern_ml":
            text = generate_analysis_summary(
                location=analysis_data["location"],
                before_date=analysis_data["before_date"],
                after_date=analysis_data["after_date"],
                result=result,
            )
        else:
            text = generate_historical_summary(
                location=analysis_data["location"],
                before_date=analysis_data["before_date"],
                after_date=analysis_data["after_date"],
                result=result,
            )

        return {
            "source": "deterministic",
            "text": text,
        }
