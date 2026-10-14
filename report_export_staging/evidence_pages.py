"""Professional supplementary evidence rendering for SetQuery PDF."""

from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth

from .formatting import NAVY, BLUE, SLATE, MUTED, BORDER


def _text(pdf, x, y, value, size=9, bold=False):
    pdf.setFillColor(NAVY if bold else SLATE)
    pdf.setFont(
        "Helvetica-Bold" if bold else "Helvetica",
        size,
    )
    pdf.drawString(x, y, str(value))


def _card(pdf, x, y, width, height):
    pdf.setFillColor(HexColor("#F8FAFC"))
    pdf.setStrokeColor(BORDER)
    pdf.roundRect(
        x, y, width, height,
        10, fill=1, stroke=1,
    )


def _metric(pdf, x, y, label, value):
    _text(pdf, x, y + 18, label, 8)
    _text(pdf, x, y, value, 12, True)


def _bar(pdf, x, y, width, value, maximum, color):
    pdf.setFillColor(HexColor("#E9EEF5"))
    pdf.roundRect(x, y, width, 9, 4, fill=1, stroke=0)

    if maximum > 0 and value > 0:
        filled = width * min(value / maximum, 1)
        pdf.setFillColor(HexColor(color))
        pdf.roundRect(
            x, y, filled, 9, 4,
            fill=1, stroke=0,
        )


def draw_burn_evidence(pdf, data, x, top, width):
    """Draw indicative NBR/dNBR evidence."""

    height = 175
    bottom = top - height

    _card(pdf, x, bottom, width, height)

    _text(pdf, x + 15, top - 24, "BURN EVIDENCE", 12, True)

    _metric(
        pdf, x + 15, top - 70,
        "Before mean NBR",
        f'{data["before_mean_nbr"]:.3f}',
    )

    _metric(
        pdf, x + 180, top - 70,
        "After mean NBR",
        f'{data["after_mean_nbr"]:.3f}',
    )

    _metric(
        pdf, x + 350, top - 70,
        "Mean dNBR",
        f'{data["mean_dnbr"]:+.3f}',
    )

    values = data.get("severity_area_km2", {})
    maximum = max(values.values(), default=0) or 1

    colors = [
        "#94A3B8",
        "#FACC15",
        "#FB923C",
        "#F97316",
        "#DC2626",
    ]

    labels = [
        "No significant change",
        "Low",
        "Moderate-low",
        "Moderate-high",
        "High",
    ]

    chart_x = x + 15
    chart_y = top - 112

    for index, ((_, value), label) in enumerate(
        zip(values.items(), labels)
    ):
        bx = chart_x + index * 98

        _bar(
            pdf,
            bx,
            chart_y,
            80,
            float(value),
            maximum,
            colors[index],
        )

        _text(pdf, bx, chart_y - 15, label, 7)

    _text(
        pdf, x + 15, bottom + 13,
        "Indicative spectral evidence; not confirmed fire detection.",
        8,
    )

    return bottom


def draw_vegetation_evidence(pdf, data, x, top, width):
    """Draw NDVI-based vegetation change."""

    height = 145
    bottom = top - height

    _card(pdf, x, bottom, width, height)

    _text(
        pdf, x + 15, top - 24,
        "VEGETATION STRESS",
        12, True,
    )

    _metric(
        pdf, x + 15, top - 70,
        "Before NDVI",
        f'{data["before_mean_ndvi"]:.3f}',
    )

    _metric(
        pdf, x + 180, top - 70,
        "After NDVI",
        f'{data["after_mean_ndvi"]:.3f}',
    )

    _metric(
        pdf, x + 350, top - 70,
        "NDVI change",
        f'{data["mean_ndvi_change"]:+.3f}',
    )

    categories = [
        ("Decreased", data["decreased_percent"], "#EF4444"),
        ("Stable", data["stable_percent"], "#94A3B8"),
        ("Increased", data["increased_percent"], "#22C55E"),
    ]

    bx = x + 15

    for label, percent, color in categories:
        _bar(pdf, bx, bottom + 34, 135, percent, 100, color)
        _text(
            pdf, bx, bottom + 17,
            f"{label}: {percent:.1f}%",
            8,
        )
        bx += 165

    return bottom


def draw_flood_evidence(pdf, data, x, top, width):
    """Draw Sentinel-1 SAR surface-water evidence."""

    height = 130
    bottom = top - height

    _card(pdf, x, bottom, width, height)

    _text(
        pdf, x + 15, top - 24,
        "FLOOD EVIDENCE",
        12, True,
    )

    _metric(
        pdf, x + 15, top - 70,
        "Before VV",
        f'{data["before_mean_vv_db"]:.2f} dB',
    )

    _metric(
        pdf, x + 180, top - 70,
        "After VV",
        f'{data["after_mean_vv_db"]:.2f} dB',
    )

    _metric(
        pdf, x + 350, top - 70,
        "New water area",
        f'{data["new_water_area_km2"]:.3f} km2',
    )

    _text(
        pdf, x + 15, bottom + 17,
        "Possible surface-water change; not confirmed flood damage.",
        8,
    )

    return bottom


def draw_selected_evidence(pdf, evidence, x=44, top=670, width=507):
    """
    Render available selected evidence.

    Returns the remaining vertical position.

    Raises if content cannot fit safely on the page.
    """

    renderers = (
        ("burn", draw_burn_evidence),
        ("vegetation", draw_vegetation_evidence),
        ("flood", draw_flood_evidence),
    )

    current_y = top
    rendered = 0

    for key, renderer in renderers:
        data = evidence.get(key)

        if data is None:
            continue

        current_y = renderer(
            pdf, data, x, current_y, width
        )

        current_y -= 16
        rendered += 1

        if current_y < 65:
            raise ValueError(
                "Evidence content exceeds available PDF page space."
            )

    if rendered == 0:
        _text(
            pdf, x, top - 35,
            "No supplementary evidence was selected.",
            10,
        )

    return current_y
