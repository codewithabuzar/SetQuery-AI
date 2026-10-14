"""Historical PDF test using recorded validation measurements."""

import json
from pathlib import Path

from report_export_staging.real_pdf_builder import (
    generate_real_report,
)

SOURCE = Path(
    "validation/historical_validation_results.json"
)

OUTPUT = Path(
    "report_export_staging/test_output"
)

OUTPUT.mkdir(parents=True, exist_ok=True)

records = json.loads(
    SOURCE.read_text(encoding="utf-8")
)

required = [
    "total_area_km2",
    "comparable_area_km2",
    "coverage_percent",
    "before_mean_ndvi",
    "after_mean_ndvi",
    "ndvi_change",
    "before_mean_mndwi",
    "after_mean_mndwi",
    "mndwi_change",
    "before_mean_ndbi",
    "after_mean_ndbi",
    "ndbi_change",
]

for index, record in enumerate(records):

    if record.get("status") != "success":
        continue

    missing = [
        key for key in required
        if key not in record
    ]

    if missing:
        print(
            f"Skipping case {index}: missing {missing}"
        )
        continue

    result = {
        key: record[key]
        for key in required
    }

    result.update({
        "before_observations": record.get(
            "before_observations"
        ),
        "after_observations": record.get(
            "after_observations"
        ),
        "warnings": record.get("warnings", []),
        "before_sensors": record.get("before_sensors", []),
        "after_sensors": record.get("after_sensors", []),
    })

    analysis_data = {
        "mode": "historical_spectral",
        "mode_label": "Historical Spectral Analysis",
        "location": record["resolved_location"],
        "latitude": record["latitude"],
        "longitude": record["longitude"],
        "before_date": record["before_date"],
        "after_date": record["after_date"],
        "radius_km": record["radius_km"],
        "approximate_resolution_m": record.get(
            "approximate_resolution_m"
        ),
        "method": record.get(
            "method",
            "Landsat spectral comparison"
        ),
        "result": result,
        "images": {},
        "change_map": {},
    }

    print(
        f"\nGenerating Historical PDF {index + 1}..."
    )

    try:
        pdf_bytes = generate_real_report(
            analysis_data,
            progress=print,
        )

        filename = OUTPUT / (
            f"historical_validation_{index + 1}.pdf"
        )

        filename.write_bytes(pdf_bytes)

        print("Saved:", filename)

    except Exception as error:
        print(
            f"FAILED case {index + 1}:",
            type(error).__name__,
            str(error),
        )
