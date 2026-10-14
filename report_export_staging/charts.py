"""Vector charts for SetQuery PDF reports."""

from reportlab.lib.colors import HexColor

from .formatting import NAVY, BLUE, MUTED, BORDER


def draw_comparison_chart(pdf, classes, x, y, width):
    """Draw Before/After land-cover comparison bars."""

    values = [
        max(item["before_km2"], item["after_km2"])
        for item in classes
    ]

    maximum = max(values, default=0) or 1

    label_width = 110
    chart_width = width - label_width - 60

    before_color = HexColor("#60A5FA")
    after_color = HexColor("#2563EB")

    for index, item in enumerate(classes):
        row_y = y - index * 68

        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x, row_y + 12, item["name"])

        before = item["before_km2"]
        after = item["after_km2"]

        for offset, value, color in (
            (0, before, before_color),
            (-18, after, after_color),
        ):
            pdf.setFillColor(color)
            pdf.roundRect(
                x + label_width,
                row_y + offset,
                max(0, chart_width * value / maximum),
                12,
                4,
                fill=1,
                stroke=0,
            )

            pdf.setFillColor(MUTED)
            pdf.setFont("Helvetica", 8)
            pdf.drawRightString(
                x + width,
                row_y + offset + 3,
                f"{value:.3f}",
            )

    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(before_color)
    pdf.drawString(x, y + 45, "BEFORE")

    pdf.setFillColor(after_color)
    pdf.drawString(x + 75, y + 45, "AFTER")


def draw_index_chart(pdf, indices, x, y, width):
    """
    Draw a structured spectral-index change chart.

    Uses equal-width categories, symmetric positive/negative
    scale, fixed plotting boundaries and centered labels.
    """

    from reportlab.lib.colors import HexColor

    positive = HexColor("#16A34A")
    negative = HexColor("#DC2626")
    grid = HexColor("#E2E8F0")
    axis = HexColor("#94A3B8")

    chart_height = 245
    chart_bottom = y - chart_height

    plot_left = x + 45
    plot_right = x + width - 25
    plot_width = plot_right - plot_left

    plot_top = y - 35
    plot_bottom = chart_bottom + 55
    plot_height = plot_top - plot_bottom

    zero_y = (plot_top + plot_bottom) / 2
    half_height = plot_height / 2

    max_abs = max(
        (abs(float(item["change"])) for item in indices),
        default=0.01,
    )

    max_abs = max(max_abs * 1.15, 0.01)

    # Graph boundary.
    pdf.setStrokeColor(grid)
    pdf.setLineWidth(0.8)

    pdf.roundRect(
        plot_left,
        plot_bottom,
        plot_width,
        plot_height,
        5,
        stroke=1,
        fill=0,
    )

    # Symmetric gridlines.
    for fraction in (-1, -0.5, 0, 0.5, 1):

        grid_y = zero_y + fraction * half_height

        pdf.setStrokeColor(
            axis if fraction == 0 else grid
        )

        pdf.setLineWidth(
            1.2 if fraction == 0 else 0.5
        )

        pdf.line(
            plot_left,
            grid_y,
            plot_right,
            grid_y,
        )

    count = len(indices)

    if count == 0:
        return

    slot_width = plot_width / count
    bar_width = min(42, slot_width * 0.35)

    for index, item in enumerate(indices):

        change = float(item["change"])

        center_x = (
            plot_left
            + (index + 0.5) * slot_width
        )

        bar_height = (
            abs(change)
            / max_abs
            * half_height
        )

        bar_bottom = (
            zero_y
            if change >= 0
            else zero_y - bar_height
        )

        pdf.setFillColor(
            positive if change >= 0 else negative
        )

        pdf.roundRect(
            center_x - bar_width / 2,
            bar_bottom,
            bar_width,
            bar_height,
            3,
            fill=1,
            stroke=0,
        )

        # Numeric value.
        value_y = (
            zero_y + bar_height + 8
            if change >= 0
            else zero_y - bar_height - 13
        )

        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 8)

        pdf.drawCentredString(
            center_x,
            value_y,
            f"{change:+.4f}",
        )

        # Category label below graph.
        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 10)

        pdf.drawCentredString(
            center_x,
            chart_bottom + 25,
            item["name"],
        )

    # Chart scale label.
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 8)

    pdf.drawString(
        plot_left,
        y + 12,
        "GREEN: Positive",
    )

    pdf.drawString(
        plot_left + 135,
        y + 12,
        "RED: Negative",
    )

    pdf.drawRightString(
        plot_right,
        y + 12,
        f"Scale: +/-{max_abs:.3f}",
    )


def draw_transition_legend(pdf, transitions, x, y):
    """Draw categorical transition colours and measured areas."""

    for index, item in enumerate(transitions):
        row_y = y - index * 30

        pdf.setFillColor(HexColor(item["color"]))
        pdf.roundRect(x, row_y, 13, 13, 3, fill=1, stroke=0)

        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x + 24, row_y + 2, item["name"])

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawRightString(
            x + 500,
            row_y + 2,
            f"{item['area_km2']:.4f} km2",
        )
