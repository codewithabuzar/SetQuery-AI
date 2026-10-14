"""Wrapped interpretation text for SetQuery PDF reports."""

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from .formatting import NAVY, SLATE, BLUE


def draw_interpretation(
    pdf,
    text,
    x,
    top,
    width,
    bottom_limit=75,
    new_page=None,
):
    """
    Draw wrapped paragraphs.

    Long text can continue onto additional pages through
    the provided new_page callback.
    """

    style = ParagraphStyle(
        "SetQueryInterpretation",
        fontName="Helvetica",
        fontSize=9,
        leading=15,
        textColor=SLATE,
        spaceAfter=10,
    )

    paragraphs = [
        part.strip()
        for part in str(text).split("\n")
        if part.strip()
    ]

    current_y = top

    for part in paragraphs:

        paragraph = Paragraph(
            part.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"),
            style,
        )

        _, height = paragraph.wrap(
            width,
            current_y - bottom_limit,
        )

        if current_y - height < bottom_limit:

            if new_page is None:
                raise ValueError(
                    "Interpretation exceeds available page space."
                )

            new_page()
            current_y = top

            _, height = paragraph.wrap(
                width,
                current_y - bottom_limit,
            )

        paragraph.drawOn(
            pdf,
            x,
            current_y - height,
        )

        current_y -= height + 13

    return current_y
