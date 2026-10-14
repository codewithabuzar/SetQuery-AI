
"""Six-page professional SetQuery trend report."""

from io import BytesIO
from html import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from .page_canvas import NumberedCanvas
from .formatting import NAVY, BLUE, SLATE, MUTED, BORDER
from .reference_map import build_reference_map
from .imagery import draw_report_image
from .tables import draw_table


MARGIN = 44
WIDTH, HEIGHT = A4
CONTENT_WIDTH = WIDTH - 2 * MARGIN

COLORS = {
    "vegetation": "#16A34A",
    "built": "#2563EB",
    "water": "#06B6D4",
    "bare": "#F59E0B",
}


def generate_trend_report(data, progress=None):
    """Generate a report from existing trend measurements."""

    periods = data["periods"]

    if not 2 <= len(periods) <= 8:
        raise ValueError("Trend report requires 2-8 periods.")

    def notify(message):
        if progress:
            progress(message)

    notify("Preparing trend measurements...")

    buffer = BytesIO()
    pdf = NumberedCanvas(buffer, pagesize=A4)

    def header(section):
        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(MARGIN, HEIGHT - 45, "SETQUERY AI")

        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(
            WIDTH - MARGIN,
            HEIGHT - 45,
            section.upper(),
        )

        pdf.setStrokeColor(BORDER)
        pdf.line(
            MARGIN, HEIGHT - 58,
            WIDTH - MARGIN, HEIGHT - 58,
        )

        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(
            MARGIN, 32,
            "SetQuery AI - Satellite Trend Report",
        )

    def title(text, subtitle=""):
        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 21)
        pdf.drawString(MARGIN, HEIGHT - 115, text)

        if subtitle:
            pdf.setFillColor(SLATE)
            pdf.setFont("Helvetica", 9)
            pdf.drawString(MARGIN, HEIGHT - 137, subtitle)

    def text(value, x, y, size=10, bold=False):
        pdf.setFillColor(NAVY if bold else SLATE)
        pdf.setFont(
            "Helvetica-Bold" if bold else "Helvetica",
            size,
        )
        pdf.drawString(x, y, str(value))

    def paragraph(value, x, top, width, size=9):
        style = ParagraphStyle(
            "TrendBody",
            fontName="Helvetica",
            fontSize=size,
            leading=14,
            textColor=SLATE,
        )

        p = Paragraph(escape(str(value)), style)
        _, h = p.wrap(width, HEIGHT)

        if h > top - 65:
            raise ValueError("Trend paragraph exceeds page.")

        p.drawOn(pdf, x, top - h)
        return top - h - 15

    def finish_page():
        pdf.showPage()

    # PAGE 1 - COVER
    notify("Creating trend report cover...")

    header("Executive overview")

    pdf.setFillColor(BLUE)
    pdf.rect(MARGIN, HEIGHT - 220, 5, 100, fill=1, stroke=0)

    text("Land-Cover", 65, HEIGHT - 160, 28, True)
    text("Trend Analysis Report", 65, HEIGHT - 198, 25, True)

    y = HEIGHT - 260
    y = paragraph(data["location"], MARGIN, y, CONTENT_WIDTH, 12)

    text(
        f'{periods[0]["date"]} to {periods[-1]["date"]}',
        MARGIN, y - 20, 11,
    )

    text(
        f'{len(periods)} observation periods',
        MARGIN, y - 65, 12, True,
    )

    text(
        f'Radius: {data["radius_km"]:g} km',
        MARGIN, y - 95, 11,
    )

    text(
        f'Total study area: {data["total_area_km2"]:.2f} km2',
        MARGIN, y - 125, 11,
    )

    text("Method: Dynamic World temporal consensus", MARGIN, 195, 10)
    text("Developer: Mohd Abuzar", MARGIN, 170, 10)

    finish_page()

    # PAGE 2 - STUDY AREA
    notify("Preparing geographic reference map...")

    header("Study area")
    title("Study Area", "Geographic context")

    try:
        reference_map = build_reference_map(
            data["latitude"],
            data["longitude"],
            data["radius_km"],
        )
    except Exception:
        reference_map = None

    draw_report_image(
        pdf, reference_map,
        MARGIN, 285,
        CONTENT_WIDTH, 350,
    )

    text(
        f'Latitude: {data["latitude"]:.5f}',
        MARGIN, 240,
    )
    text(
        f'Longitude: {data["longitude"]:.5f}',
        MARGIN, 218,
    )
    text(
        f'Analysis radius: {data["radius_km"]:g} km',
        MARGIN, 196,
    )

    text(
        "Reference map: OpenStreetMap contributors",
        MARGIN, 160, 8,
    )

    finish_page()

    # PAGE 3 - COMPOSITION
    notify("Rendering land-cover composition chart...")

    header("Land-cover composition")
    title(
        "Land-Cover Composition",
        "Percentages relative to each period's valid area",
    )

    categories = [
        ("Vegetation", "vegetation"),
        ("Built-up", "built"),
        ("Water", "water"),
        ("Bare", "bare"),
    ]

    y = 640

    for period in periods:
        date_label = str(period["date"])
        text(date_label, MARGIN, y, 10, True)

        percentages = {
            "vegetation": float(
                period["vegetation_percent_of_valid_area"]
            ),
            "built": float(
                period["built_percent_of_valid_area"]
            ),
            "water": float(
                period["water_percent_of_valid_area"]
            ),
            "bare": float(
                period["bare_percent_of_valid_area"]
            ),
        }

        bar_x = MARGIN + 120
        bar_width = 350
        current_x = bar_x

        for label, key in categories:
            percentage = percentages[key]

            if not 0 <= percentage <= 100:
                raise ValueError(
                    f"Invalid trend percentage for {key}: "
                    f"{percentage}"
                )

            segment = bar_width * percentage / 100

            if segment > 0:
                pdf.setFillColor(HexColor(COLORS[key]))
                pdf.rect(
                    current_x,
                    y - 3,
                    segment,
                    14,
                    fill=1,
                    stroke=0,
                )

            current_x += segment

        y -= 62

    legend_y = 100

    for index, (label, key) in enumerate(categories):
        x = MARGIN + index * 125

        pdf.setFillColor(HexColor(COLORS[key]))
        pdf.rect(x, legend_y, 12, 12, fill=1, stroke=0)

        text(label, x + 17, legend_y + 2, 8)

    finish_page()

    # PAGE 4 - MEASUREMENTS
    notify("Formatting per-date measurements...")

    header("Per-date measurements")
    title(
        "Land-Cover Measurements",
        "Measured areas in square kilometres",
    )

    measurement_rows = []

    for period in periods:
        measurement_rows.append([
            str(period["date"]),
            f'{period["vegetation_km2"]:.3f}',
            f'{period["built_km2"]:.3f}',
            f'{period["water_km2"]:.3f}',
            f'{period["bare_km2"]:.3f}',
        ])

    draw_table(
        pdf,
        headers=[
            "Date",
            "Vegetation",
            "Built-up",
            "Water",
            "Bare",
        ],
        rows=measurement_rows,
        x=MARGIN,
        top=670,
        widths=[107, 100, 100, 100, 100],
        font_size=8,
        numeric_columns=[1, 2, 3, 4],
    )

    text(
        "All area measurements are expressed in km2.",
        MARGIN,
        125,
        9,
    )

    text(
        "Each observation period is analyzed independently.",
        MARGIN,
        105,
        9,
    )

    finish_page()

    # PAGE 5 - COVERAGE
    notify("Rendering observation reliability...")

    header("Coverage and reliability")

    title(
        "Coverage & Reliability",
        "Valid coverage and observation support",
    )

    # Coverage chart using measured percentages.
    y = 650

    for period in periods:
        coverage = float(period["coverage_percent"])

        if not 0 <= coverage <= 100:
            raise ValueError(
                f"Invalid coverage percentage: {coverage}"
            )

        text(
            str(period["date"]),
            MARGIN,
            y,
            9,
            True,
        )

        pdf.setFillColor(HexColor("#E5E7EB"))
        pdf.roundRect(
            165,
            y - 3,
            260,
            12,
            4,
            fill=1,
            stroke=0,
        )

        pdf.setFillColor(
            HexColor("#16A34A")
            if period["reliable"]
            else HexColor("#F59E0B")
        )

        pdf.roundRect(
            165,
            y - 3,
            260 * coverage / 100,
            12,
            4,
            fill=1,
            stroke=0,
        )

        text(
            f"{coverage:.1f}%",
            445,
            y,
            9,
        )

        y -= 48

    table_top = y - 20

    reliability_rows = []

    for period in periods:
        reliability_rows.append([
            str(period["date"]),
            f'{period["coverage_percent"]:.1f}%',
            str(period["observations"]),
            "Yes" if period["reliable"] else "No",
        ])

    # Estimate table space before rendering.
    # Each row uses approximately 30 PDF points.
    estimated_table_height = (
        len(reliability_rows) + 1
    ) * 30

    if table_top - estimated_table_height < 75:

        finish_page()

        header("Coverage details")
        title(
            "Observation Reliability",
            "Per-date coverage and observation measurements",
        )

        table_top = 670

    draw_table(
        pdf,
        headers=[
            "Date",
            "Coverage",
            "Observations",
            "Reliable",
        ],
        rows=reliability_rows,
        x=MARGIN,
        top=table_top,
        widths=[130, 120, 137, 120],
        font_size=8,
        numeric_columns=[1, 2],
    )

    finish_page()

    # PAGE 6 - METHODOLOGY
    notify("Preparing methodology and limitations...")

    header("Methodology")
    title("Methodology & Limitations")

    notes = [
        data.get("methodology_note", ""),
        "Each date is analyzed independently.",
        "Valid pixels can differ between periods.",
        "Coverage is not classification accuracy.",
        "These results do not measure pairwise transitions.",
        "Satellite-derived estimates are not surveyed ground truth.",
    ]

    y = 650

    for note in notes:
        if note:
            y = paragraph(note, MARGIN, y, CONTENT_WIDTH)

    warnings = data.get("warnings", [])

    for warning in warnings:
        if y < 100:
            break
        y = paragraph(warning, MARGIN, y, CONTENT_WIDTH)

    finish_page()

    notify("Finalizing trend PDF...")

    pdf.save()

    notify("Trend report ready.")

    return buffer.getvalue()
