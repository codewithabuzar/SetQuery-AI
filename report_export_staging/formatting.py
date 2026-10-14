"""Formatting utilities for SetQuery PDF reports."""

from datetime import datetime
from reportlab.lib.colors import HexColor

NAVY = HexColor("#101828")
BLUE = HexColor("#2563EB")
LIGHT_BLUE = HexColor("#EFF6FF")
SLATE = HexColor("#475467")
MUTED = HexColor("#667085")
BORDER = HexColor("#E4E7EC")
WHITE = HexColor("#FFFFFF")
GREEN = HexColor("#16A34A")
RED = HexColor("#DC2626")

PAGE_MARGIN = 44


def format_number(value, decimals=2):
    if value is None:
        return "N/A"
    return f"{float(value):,.{decimals}f}"


def format_area(value, decimals=3):
    return f"{format_number(value, decimals)} km2"


def format_percent(value):
    return f"{format_number(value, 1)}%"


def format_date(value):
    try:
        return datetime.fromisoformat(
            str(value)
        ).strftime("%d %B %Y")
    except (ValueError, TypeError):
        return str(value)
