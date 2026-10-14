"""Professional paginated text rendering for SetQuery reports."""

from html import escape

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from .formatting import NAVY, SLATE, BLUE


BODY_STYLE = ParagraphStyle(
    "SetQueryBody",
    fontName="Helvetica",
    fontSize=9,
    leading=15,
    textColor=SLATE,
)

HEADING_STYLE = ParagraphStyle(
    "SetQueryHeading",
    fontName="Helvetica-Bold",
    fontSize=12,
    leading=17,
    textColor=NAVY,
)


def draw_report_text(
    pdf,
    sections,
    new_page,
    start_y=650,
    left=44,
    width=507,
    bottom=75,
):
    """
    Render titled text sections with automatic pagination.

    new_page must finish the current page and draw
    the header/title on the following page.

    Returns the final vertical position.
    """

    y = start_y

    def draw_paragraph(text, style, gap):
        nonlocal y

        paragraph = Paragraph(
            escape(str(text)).replace("\n", "<br/>"),
            style,
        )

        available_height = start_y - bottom

        remaining = [paragraph]

        while remaining:
            current = remaining.pop(0)

            _, required = current.wrap(
                width,
                available_height,
            )

            if required <= y - bottom:
                current.drawOn(
                    pdf,
                    left,
                    y - required,
                )
                y -= required + gap
                continue

            if y <= bottom + 30:
                new_page()
                y = start_y
                remaining.insert(0, current)
                continue

            parts = current.split(
                width,
                y - bottom,
            )

            if not parts:
                new_page()
                y = start_y
                remaining.insert(0, current)
                continue

            first = parts[0]
            _, first_height = first.wrap(
                width,
                y - bottom,
            )

            first.drawOn(
                pdf,
                left,
                y - first_height,
            )

            remaining = parts[1:] + remaining

            if remaining:
                new_page()
                y = start_y
            else:
                y -= first_height + gap

    for heading, paragraphs in sections:

        if y < bottom + 65:
            new_page()
            y = start_y

        draw_paragraph(
            heading,
            HEADING_STYLE,
            10,
        )

        for text in paragraphs:
            if text:
                draw_paragraph(
                    text,
                    BODY_STYLE,
                    12,
                )

        y -= 12

    return y
