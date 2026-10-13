
"""Local answers to verified SetQuery application questions."""

from ai_knowledge import get_app_knowledge


def answer_app_question(question):
    q = " ".join(question.casefold().split())
    info = get_app_knowledge()

    creator_terms = (
        "creator", "developer", "founder", "who made",
        "who built", "who created", "who developed",
        "kisne banaya", "kisne banayi", "kisne develop",
        "kaun banaya", "kaun developer", "who is behind",
    )

    if any(term in q for term in creator_terms):
        return (
            "SetQuery AI was developed by Mohd Abuzar. "
            "GitHub: " + info["github_profile"] + ". "
            "Project: " + info["github_repository"]
        )

    topics = (
        (
            ("burn evidence", "dnbr", "nbr", "burn analysis"),
            "burn_evidence", "burn_usage"
        ),
        (
            ("vegetation stress", "ndvi", "crop stress"),
            "vegetation_stress", "vegetation_usage"
        ),
        (
            ("flood evidence", "flood analysis", "sar"),
            "flood_evidence", "flood_usage"
        ),
        (
            ("trend analysis", "trend mode", "trend over time"),
            "trend_analysis", None
        ),
        (
            ("historical mode", "historical analysis", "landsat"),
            "historical_analysis", "modern_vs_historical"
        ),
        (
            ("modern mode", "modern analysis", "dynamic world"),
            "modern_analysis", "modern_vs_historical"
        ),
        (
            ("change map", "change detection"),
            "change_detection", None
        ),
        (
            ("temporal consensus", "confidence threshold"),
            "temporal_consensus", None
        ),
        (
            ("how to use", "how do i use", "how to start",
             "kaise use", "kaise chalaye", "how to analyze"),
            "usage_guide", None
        ),
        (
            ("technology stack", "tech stack", "technologies",
             "which technologies", "kis technology"),
            "technology_stack", None
        ),
        (
            ("limitation", "limitations", "accuracy"),
            "scientific_limits", None
        ),
        (
            ("github", "source code", "open source",
             "repository", "license", "contribute"),
            "github_repository", "license"
        ),
        (
            ("slow", "not working", "low coverage",
             "troubleshoot", "error"),
            "troubleshooting", None
        ),
    )

    for keywords, primary, secondary in topics:
        if any(word in q for word in keywords):
            parts = [info[primary]]
            if secondary:
                parts.append(info[secondary])
            return " ".join(parts)

    general = (
        "what is setquery", "what is this app",
        "about this app", "about setquery",
        "what can this app", "what does setquery",
        "features of", "all features",
        "app ke bare", "app ke baare",
        "ye app kya", "setquery kya",
    )

    if any(word in q for word in general):
        keys = (
            "purpose", "location_selection", "study_area",
            "modern_analysis", "historical_analysis",
            "trend_analysis", "change_detection",
            "burn_evidence", "vegetation_stress",
            "flood_evidence", "ai_assistant",
            "scientific_limits",
        )
        return "\n\n".join(
            "- " + info[key] for key in keys
        )

    return None
