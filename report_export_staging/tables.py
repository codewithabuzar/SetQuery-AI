"""Professional table rendering for SetQuery PDF reports."""

from html import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from .formatting import NAVY, SLATE, BORDER, WHITE


HEADER_BACKGROUND = HexColor("#17365D")
ALTERNATE_BACKGROUND = HexColor("#F1F5F9")


def draw_table(
    pdf,
    headers,
    rows,
    x,
    top,
    widths,
    font_size=8,
    padding=8,
    min_y=65,
    numeric_columns=None,
):
    """
    Draw a professional PDF table.

    Parameters
    ----------
    pdf:
        ReportLab canvas.

    headers:
        List of column headings.

    rows:
        List of row sequences.

    x:
        Left position.

    top:
        Top position.

    widths:
        Column widths in PDF points.

    min_y:
        Lowest permitted table position.

    numeric_columns:
        Column indices aligned to the right.

    Returns
    -------
    float:
        Bottom position of the completed table.

    Raises
    ------
    ValueError:
        If the table would exceed the available page space.
    """

    numeric_columns = set(numeric_columns or [])

    if len(headers) != len(widths):
        raise ValueError(
            "Header count must match column widths."
        )

    if any(width <= 0 for width in widths):
        raise ValueError(
            "Column widths must be positive."
        )

    header_style = ParagraphStyle(
        "SetQueryTableHeader",
        fontName="Helvetica-Bold",
        fontSize=font_size,
        leading=font_size + 3,
        textColor=WHITE,
    )

    body_style = ParagraphStyle(
        "SetQueryTableBody",
        fontName="Helvetica",
        fontSize=font_size,
        leading=font_size + 3,
        textColor=SLATE,
    )

    right_style = ParagraphStyle(
        "SetQueryTableNumeric",
        parent=body_style,
        alignment=2,
    )

    def prepare_cells(values, header=False):
        if len(values) != len(widths):
            raise ValueError(
                "Table row has incorrect column count."
            )

        cells = []
        heights = []

        for index, value in enumerate(values):
            if header:
                if index in numeric_columns:
                    style = ParagraphStyle(
                        "SetQueryNumericHeader",
                        parent=header_style,
                        alignment=2,
                    )
                else:
                    style = header_style

            else:
                style = (
                    right_style
                    if index in numeric_columns
                    else body_style
                )

            paragraph = Paragraph(
                escape(str(value)),
                style,
            )

            available_width = widths[index] - 2 * padding

            if available_width <= 0:
                raise ValueError(
                    "Column width is too small for padding."
                )

            _, height = paragraph.wrap(
                available_width,
                1000,
            )

            cells.append(paragraph)
            heights.append(height)

        row_height = max(heights, default=0) + 2 * padding

        return cells, row_height

    prepared = [
        prepare_cells(headers, header=True)
    ]

    for row in rows:
        prepared.append(
            prepare_cells(row)
        )

    total_height = sum(
        row_height
        for _, row_height in prepared
    )

    if top - total_height < min_y:
        raise ValueError(
            "Table exceeds available PDF page space. "
            "Move it to another page or paginate the rows."
        )

    current_top = top
    table_width = sum(widths)

    for row_index, (cells, row_height) in enumerate(prepared):

        bottom = current_top - row_height

        if row_index == 0:
            background = HEADER_BACKGROUND

        elif row_index % 2 == 0:
            background = ALTERNATE_BACKGROUND

        else:
            background = WHITE

        pdf.setFillColor(background)

        pdf.rect(
            x,
            bottom,
            table_width,
            row_height,
            fill=1,
            stroke=0,
        )

        current_x = x

        for index, paragraph in enumerate(cells):

            available_width = widths[index] - 2 * padding

            _, paragraph_height = paragraph.wrap(
                available_width,
                row_height,
            )

            paragraph.drawOn(
                pdf,
                current_x + padding,
                current_top - padding - paragraph_height,
            )

            current_x += widths[index]

        pdf.setStrokeColor(BORDER)
        pdf.setLineWidth(0.4)

        pdf.line(
            x,
            bottom,
            x + table_width,
            bottom,
        )

        current_top = bottom

    return current_top
