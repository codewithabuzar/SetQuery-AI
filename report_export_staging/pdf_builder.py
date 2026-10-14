"""Six-page SetQuery PDF report prototype."""

from io import BytesIO
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor

from .formatting import (
    NAVY, BLUE, SLATE, MUTED, BORDER,
    LIGHT_BLUE, WHITE, PAGE_MARGIN,
    format_number, format_area, format_percent, format_date,
)


def generate_report_preview(
    location="Rajasthan, India",
    before_date="2022-09-15",
    after_date="2025-09-15",
    radius_km=10,
):
    """Generate a six-page PDF layout prototype."""

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4

    def header(page_number, section):
        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(PAGE_MARGIN, height - 45, "SETQUERY AI")

        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(
            width - PAGE_MARGIN,
            height - 45,
            section.upper(),
        )

        pdf.setStrokeColor(BORDER)
        pdf.line(
            PAGE_MARGIN,
            height - 58,
            width - PAGE_MARGIN,
            height - 58,
        )

        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(
            PAGE_MARGIN,
            32,
            "Satellite-derived estimates | SetQuery AI",
        )
        pdf.drawRightString(
            width - PAGE_MARGIN,
            32,
            f"{page_number} / 6",
        )

    def title(text, subtitle=None):
        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 23)
        pdf.drawString(PAGE_MARGIN, height - 115, text)

        if subtitle:
            pdf.setFillColor(SLATE)
            pdf.setFont("Helvetica", 10)
            pdf.drawString(
                PAGE_MARGIN,
                height - 138,
                subtitle,
            )

    def card(x, y, w, h, heading, value):
        pdf.setFillColor(LIGHT_BLUE)
        pdf.roundRect(x, y, w, h, 10, fill=1, stroke=0)

        pdf.setFillColor(SLATE)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x + 14, y + h - 23, heading)

        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(x + 14, y + 20, str(value))

    # PAGE 1
    header(1, "Executive overview")

    pdf.setFillColor(BLUE)
    pdf.rect(PAGE_MARGIN, height - 225, 5, 95, fill=1, stroke=0)

    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 29)
    pdf.drawString(65, height - 160, "Satellite Change")
    pdf.drawString(65, height - 195, "Analysis Report")

    pdf.setFillColor(SLATE)
    pdf.setFont("Helvetica", 13)
    pdf.drawString(PAGE_MARGIN, height - 260, location)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        PAGE_MARGIN,
        height - 288,
        f"{format_date(before_date)}  -  {format_date(after_date)}",
    )

    card(44, 360, 245, 85, "Study radius", f"{radius_km} km")
    card(306, 360, 245, 85, "Analysis mode", "Modern ML")

    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        PAGE_MARGIN,
        190,
        "Prepared using Google Earth Engine satellite measurements.",
    )
    pdf.drawString(
        PAGE_MARGIN,
        169,
        "Developed by Mohd Abuzar.",
    )

    pdf.showPage()

    # PAGE 2
    header(2, "Study area and imagery")
    title("Study Area", "Geographic context and satellite observations")

    card(44, 570, 245, 80, "Location", location[:28])
    card(306, 570, 245, 80, "Radius", f"{radius_km} km")

    pdf.setFillColor(LIGHT_BLUE)
    pdf.roundRect(44, 320, 507, 210, 10, fill=1, stroke=0)

    pdf.setFillColor(SLATE)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawCentredString(width / 2, 425, "REFERENCE MAP")
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width / 2, 405, "High-resolution map placeholder")

    pdf.showPage()

    # PAGE 3
    header(3, "Change detection")
    title("Change Detection", "Land-cover transition visualization")

    pdf.setFillColor(LIGHT_BLUE)
    pdf.roundRect(44, 285, 507, 380, 10, fill=1, stroke=0)

    pdf.setFillColor(SLATE)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawCentredString(width / 2, 475, "CHANGE MAP")
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width / 2, 455, "High-resolution change map placeholder")

    pdf.showPage()

    # PAGE 4
    header(4, "Statistics")
    title("Land-Cover Statistics", "Measured before and after comparison")

    chart_values = [
        ("Vegetation", 0.73),
        ("Built-up", 0.42),
        ("Water", 0.28),
        ("Bare", 0.54),
    ]

    y = 625

    for label, ratio in chart_values:
        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(44, y + 17, label)

        pdf.setFillColor(LIGHT_BLUE)
        pdf.roundRect(44, y - 8, 507, 15, 5, fill=1, stroke=0)

        pdf.setFillColor(BLUE)
        pdf.roundRect(44, y - 8, 507 * ratio, 15, 5, fill=1, stroke=0)

        y -= 95

    pdf.showPage()

    # PAGE 5
    header(5, "Supplementary evidence")
    title("Supplementary Evidence", "Optional environmental indicators")

    sections = [
        ("Burn Evidence", "NBR / dNBR"),
        ("Vegetation Stress", "NDVI change"),
        ("Flood Evidence", "Sentinel-1 SAR"),
    ]

    y = 590

    for heading, detail in sections:
        card(44, y, 507, 85, heading, detail)
        y -= 115

    pdf.showPage()

    # PAGE 6
    header(6, "Methodology")
    title("Methodology & Limitations", "Scientific interpretation and report metadata")

    notes = [
        "Satellite measurements are estimates, not surveyed ground truth.",
        "Comparable coverage is not classification accuracy.",
        "Target dates represent composite windows.",
        "Spectral evidence does not establish exact causes.",
        "Property-level changes require independent verification.",
    ]

    y = 620

    for note in notes:
        pdf.setFillColor(BLUE)
        pdf.circle(50, y + 3, 3, fill=1, stroke=0)

        pdf.setFillColor(SLATE)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(65, y, note)
        y -= 35

    pdf.save()
    buffer.seek(0)

    return buffer.getvalue()
