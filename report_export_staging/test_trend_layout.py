"""Local Trend PDF layout tests using synthetic data."""

from pathlib import Path

from report_export_staging.trend_pdf_builder import (
    generate_trend_report,
)

OUTPUT = Path("report_export_staging/test_output")
OUTPUT.mkdir(exist_ok=True)

for count in (2, 4, 6, 8):

    periods = []

    for index in range(count):

        periods.append({
            "date": f"{2018 + index}-06-01",
            "vegetation_km2": 4.0 + index * 0.1,
            "built_km2": 2.0 + index * 0.05,
            "water_km2": 1.0,
            "bare_km2": 0.5,
            "vegetation_percent_of_valid_area": 53.3,
            "built_percent_of_valid_area": 26.7,
            "water_percent_of_valid_area": 13.3,
            "bare_percent_of_valid_area": 6.7,
            "coverage_percent": 88.0 - index,
            "observations": 15 + index,
            "reliable": index % 3 != 0,
        })

    data = {
        "location": "Synthetic PDF Layout Test Area",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "radius_km": 2.0,
        "total_area_km2": 12.57,
        "periods": periods,
        "methodology_note": (
            "Synthetic measurements used exclusively "
            "to verify PDF layout and pagination."
        ),
        "warnings": [
            "Synthetic test data. Not satellite measurements."
        ],
    }

    pdf_bytes = generate_trend_report(data)

    output = OUTPUT / f"trend_{count}_periods.pdf"
    output.write_bytes(pdf_bytes)

    print(f"Generated: {output}")
