from .report_text import draw_report_text
from .page_canvas import NumberedCanvas
"""Real-data SetQuery PDF report renderer."""

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

from .imagery import (
    fetch_report_image,
    draw_report_image,
)

from .reference_map import build_reference_map
from .high_res_imagery import get_modern_high_res_images
from .evidence_pages import draw_selected_evidence
from .data_adapter import prepare_report_data
from .charts import (
    draw_comparison_chart,
    draw_index_chart,
    draw_transition_legend,
)
from .tables import draw_table


def generate_real_report(analysis_data, progress=None, evidence=None, interpretation=None, preset='Standard'):
    """
    Generate a six-page analysis report using actual data.

    No satellite analysis or Earth Engine request occurs here.
    """

    if preset not in ("Standard", "Detailed"):
        raise ValueError("Unsupported PDF report preset.")

    report = prepare_report_data(analysis_data)

    def notify(message):
        if progress is not None:
            progress(message)

    notify("Preparing satellite imagery...")

    downloaded_images = {}

    for name in ("before_url", "after_url", "change_url"):
        url = report["images"].get(name)

        if not url:
            downloaded_images[name] = None
            continue

        try:
            downloaded_images[name] = fetch_report_image(url)
        except Exception:
            downloaded_images[name] = None

    # High-resolution imagery is requested only during
    # explicit PDF generation, never during normal analysis.

    if report["mode"] == "modern_ml":

        notify("Preparing high-resolution Sentinel-2 imagery...")

        try:
            high_res_images = get_modern_high_res_images(
                analysis_data
            )

            for name in ("before_url", "after_url"):
                if high_res_images.get(name) is not None:
                    downloaded_images[name] = high_res_images[name]

            notify("High-resolution imagery prepared.")

        except Exception as error:
            notify(
                "High-resolution imagery unavailable; "
                "using existing satellite previews."
            )

    notify("Preparing geographic reference map...")

    try:
        reference_map = build_reference_map(
            latitude=report["latitude"],
            longitude=report["longitude"],
            radius_km=report["radius_km"],
        )
    except Exception:
        reference_map = None
        notify("Reference map unavailable; continuing report.")

    notify("Arranging report pages...")

    buffer = BytesIO()
    pdf = NumberedCanvas(buffer, pagesize=A4)

    width, height = A4

    def header(page_number, section):
        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(44, height - 45, "SETQUERY AI")

        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(MUTED)
        pdf.drawRightString(
            width - 44,
            height - 45,
            section.upper(),
        )

        pdf.setStrokeColor(BORDER)
        pdf.line(44, height - 58, width - 44, height - 58)

        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(MUTED)
        pdf.drawString(44, 32, "SetQuery AI - Satellite Analysis Report")
        # Total page numbering is handled by NumberedCanvas.

    def title(text, subtitle=None):
        pdf.setFont("Helvetica-Bold", 23)
        pdf.setFillColor(NAVY)
        pdf.drawString(44, height - 115, text)

        if subtitle:
            pdf.setFont("Helvetica", 10)
            pdf.setFillColor(SLATE)
            pdf.drawString(44, height - 138, subtitle)

    def card(x, y, w, h, label, value):
        pdf.setFillColor(LIGHT_BLUE)
        pdf.roundRect(x, y, w, h, 9, fill=1, stroke=0)

        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(SLATE)
        pdf.drawString(x + 14, y + h - 23, label)

        pdf.setFont("Helvetica-Bold", 14)
        pdf.setFillColor(NAVY)
        pdf.drawString(x + 14, y + 20, str(value)[:30])

    # PAGE 1: OVERVIEW

    header(1, "Executive overview")

    pdf.setFillColor(BLUE)
    pdf.rect(44, height - 220, 5, 95, fill=1, stroke=0)

    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(65, height - 160, "Satellite Change")
    pdf.drawString(65, height - 195, "Analysis Report")

    pdf.setFont("Helvetica", 12)
    pdf.setFillColor(SLATE)
    pdf.drawString(44, height - 260, report["location"][:65])

    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        44,
        height - 288,
        f'{format_date(report["before_date"])} - '
        f'{format_date(report["after_date"])}',
    )

    card(44, 365, 245, 80, "Analysis mode", report["mode_label"])
    card(306, 365, 245, 80, "Study radius", f'{report["radius_km"]:g} km')

    card(
        44, 255, 245, 80,
        "Comparable coverage",
        format_percent(report["coverage_percent"]),
    )

    card(
        306, 255, 245, 80,
        "Comparable area",
        format_area(report["comparable_area_km2"]),
    )

    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(44, 170, "Prepared using satellite-derived measurements.")
    pdf.drawString(44, 152, "Developed by Mohd Abuzar.")

    pdf.showPage()

    # PAGE 2: STUDY AREA AND SATELLITE IMAGERY

    header(2, "Study area and imagery")
    title(
        "Study Area & Satellite Imagery",
        "Geographic context and before/after comparison",
    )

    draw_report_image(
        pdf,
        reference_map,
        44, 395, 507, 235,
        "Reference map - OpenStreetMap contributors",
    )

    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(44, 355, "BEFORE")
    pdf.drawString(306, 355, "AFTER")

    draw_report_image(
        pdf,
        downloaded_images["before_url"],
        44, 165, 245, 175,
        format_date(report["before_date"]),
    )

    draw_report_image(
        pdf,
        downloaded_images["after_url"],
        306, 165, 245, 175,
        format_date(report["after_date"]),
    )

    pdf.setFillColor(SLATE)
    pdf.setFont("Helvetica", 9)

    pdf.drawString(
        44, 105,
        f'Latitude: {report["latitude"]:.5f}',
    )

    pdf.drawString(
        306, 105,
        f'Longitude: {report["longitude"]:.5f}',
    )

    pdf.drawString(
        44, 88,
        f'Radius: {report["radius_km"]:g} km',
    )

    pdf.drawString(
        306, 88,
        f'Coverage: {report["coverage_percent"]:.1f}%',
    )

    pdf.showPage()

    # PAGE 3: CHANGE DETECTION

    header(3, "Change detection")

    if report["mode"] == "modern_ml":

        title(
            "Change Detection",
            "Dynamic World land-cover transitions",
        )

        # Compact change map leaves space for numerical measurements.

        draw_report_image(
            pdf,
            downloaded_images["change_url"],
            44, 405, 507, 235,
        )

        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(
            44,
            378,
            "MEASURED LAND-COVER TRANSITIONS",
        )

        transition_rows = [
            [
                item["name"],
                f'{item["area_km2"]:.4f}',
            ]
            for item in report["transitions"]
        ]

        draw_table(
            pdf,
            headers=[
                "Transition",
                "Measured area (km2)",
            ],
            rows=transition_rows,
            x=44,
            top=358,
            widths=[340, 167],
            numeric_columns=[1],
        )

        # Preserve transition colours in a compact legend.

        legend_y = 130

        for index, item in enumerate(report["transitions"]):

            legend_x = 44 + (index % 3) * 170
            row_y = legend_y - (index // 3) * 24

            pdf.setFillColor(HexColor(item["color"]))
            pdf.roundRect(
                legend_x,
                row_y,
                10,
                10,
                2,
                fill=1,
                stroke=0,
            )

            pdf.setFillColor(SLATE)
            pdf.setFont("Helvetica", 7)
            pdf.drawString(
                legend_x + 15,
                row_y + 1,
                item["name"],
            )

        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(
            44,
            68,
            "Transition areas use original classified pixels.",
        )

    else:

        title(
            "Historical Spectral Change",
            "Landsat NDVI, MNDWI and NDBI indicators",
        )

        draw_index_chart(
            pdf,
            report["indices"],
            44,
            600,
            507,
        )

        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(
            44, 320,
            "Spectral differences are not categorical",
        )
        pdf.drawString(
            44, 305,
            "land-cover transition measurements.",
        )

    pdf.showPage()

    # PAGE 4: STATISTICS

    header(4, "Statistics")

    if report["mode"] == "modern_ml":

        title(
            "Land-Cover Statistics",
            "Before and after class areas",
        )

        draw_comparison_chart(
            pdf,
            report["classes"],
            44,
            610,
            507,
        )

        table_heading_y = 330
        table_top = 310

        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(
            44,
            table_heading_y,
            "LAND-COVER MEASUREMENTS",
        )

        rows = []

        for item in report["classes"]:
            before = item["before_km2"]
            after = item["after_km2"]

            rows.append([
                item["name"],
                f"{before:.3f}",
                f"{after:.3f}",
                f"{after - before:+.3f}",
            ])

        table_bottom = draw_table(
            pdf,
            headers=[
                "Land-cover class",
                "Before km2",
                "After km2",
                "Net change km2",
            ],
            rows=rows,
            x=44,
            top=table_top,
            widths=[165, 110, 110, 122],
            numeric_columns=[1, 2, 3],
        )

    else:

        title(
            "Spectral Statistics",
            "Measured index differences",
        )

        draw_index_chart(
            pdf,
            report["indices"],
            44,
            610,
            507,
        )

        table_heading_y = 355
        table_top = 335

        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(
            44,
            table_heading_y,
            "SPECTRAL INDEX MEASUREMENTS",
        )

        rows = []

        for item in report["indices"]:
            rows.append([
                item["name"],
                f'{item["before"]:+.4f}',
                f'{item["after"]:+.4f}',
                f'{item["change"]:+.4f}',
            ])

        table_bottom = draw_table(
            pdf,
            headers=[
                "Index",
                "Before",
                "After",
                "Difference",
            ],
            rows=rows,
            x=44,
            top=table_top,
            widths=[150, 119, 119, 119],
            numeric_columns=[1, 2, 3],
        )

        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(
            44,
            table_bottom - 25,
            "Spectral indices are dimensionless measurements.",
        )

    pdf.showPage()

    # SUPPLEMENTARY EVIDENCE
    # Render only when evidence was requested and calculated.

    evidence = evidence or {}

    if evidence:

        header(5, "Supplementary evidence")

        title(
            "Supplementary Evidence",
            "Selected environmental indicators",
        )

        notify("Rendering supplementary evidence...")

        draw_selected_evidence(
            pdf,
            evidence,
            x=44,
            top=670,
            width=507,
        )

        pdf.showPage()

    # PAGE 6: INTERPRETATION AND METHODOLOGY

    from report import generate_analysis_summary
    from historical_report import generate_historical_summary

    methodology_page = 6 if evidence else 5

    header(
        methodology_page,
        "Interpretation and methodology",
    )

    title(
        "Interpretation & Methodology",
        "Measured findings and scientific limitations",
    )

    if report["mode"] == "modern_ml":
        summary = generate_analysis_summary(
            location=analysis_data["location"],
            before_date=analysis_data["before_date"],
            after_date=analysis_data["after_date"],
            result=analysis_data["result"],
        )
    else:
        summary = generate_historical_summary(
            location=analysis_data["location"],
            before_date=analysis_data["before_date"],
            after_date=analysis_data["after_date"],
            result=analysis_data["result"],
        )

    sections = [
        (
            "Analysis Summary",
            [summary],
        ),
        (
            "Methodology",
            [
                str(analysis_data.get(
                    "method",
                    report["mode_label"],
                )),
                (
                    "Results are derived from satellite "
                    "observations and represent estimates, "
                    "not surveyed ground truth."
                ),
            ],
        ),
        (
            "Coverage",
            [
                (
                    f'Comparable coverage: '
                    f'{report["coverage_percent"]:.1f}%. '
                    "Coverage describes the portion of the "
                    "study area with valid comparable data. "
                    "It is not classification accuracy."
                ),
            ],
        ),
        (
            "Limitations",
            [
                "Target dates represent composite windows.",
                (
                    "Measured differences do not establish "
                    "their underlying causes."
                ),
                (
                    "Individual-property changes require "
                    "independent verification."
                ),
            ],
        ),
    ]

    if preset == "Detailed":

        detail_notes = [
            (
                "Analysis mode: "
                + str(report["mode_label"])
            ),
            (
                "Study location: "
                + str(report["location"])
            ),
            (
                "Coordinates: "
                f'{report["latitude"]:.6f}, '
                f'{report["longitude"]:.6f}'
            ),
            (
                "Study radius: "
                f'{report["radius_km"]:g} km'
            ),
            (
                "Total study area: "
                f'{report["total_area_km2"]:.3f} km2'
            ),
            (
                "Comparable area: "
                f'{report["comparable_area_km2"]:.3f} km2'
            ),
            (
                "Comparable coverage: "
                f'{report["coverage_percent"]:.2f}%'
            ),
        ]

        observations = report.get("observations", {})

        for period_name in ("before", "after"):
            count = observations.get(period_name)

            if count is not None:
                detail_notes.append(
                    f"{period_name.title()} observations: "
                    + str(count)
                )

        if report["mode"] == "modern_ml":

            detail_notes.append(
                "Dynamic World categorical areas and "
                "transitions are satellite-derived estimates."
            )

        else:

            detail_notes.append(
                "NDVI, MNDWI and NDBI are dimensionless "
                "spectral indices. Their changes must not "
                "be interpreted as categorical land-cover "
                "transition areas."
            )

        sections.append(
            (
                "Detailed Analysis Metadata",
                detail_notes,
            )
        )

    if report["warnings"]:
        sections.append(
            (
                "Analysis Warnings",
                report["warnings"],
            )
        )

    if interpretation is not None:
        sections.append(
            (
                "Optional AI Interpretation",
                [
                    interpretation["text"],
                    (
                        "Interpretation source: "
                        + interpretation["source"]
                    ),
                ],
            )
        )

    continuation_number = methodology_page

    def new_text_page():
        nonlocal continuation_number

        pdf.showPage()
        continuation_number += 1

        header(
            continuation_number,
            "Interpretation continued",
        )

        title(
            "Report Notes",
            "Continued interpretation and methodology",
        )

    draw_report_text(
        pdf,
        sections,
        new_page=new_text_page,
        start_y=650,
    )

    pdf.showPage()

    notify("Finalizing PDF document...")

    pdf.save()
    buffer.seek(0)

    notify("Report ready.")

    return buffer.getvalue()
