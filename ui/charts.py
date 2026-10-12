"""
Altair chart components for SetQuery.
"""

import altair as alt


# ==========================================================
# HELPER FUNCTIONS (Internal to charts module)
# ==========================================================

def _paired_values(result, mapping, category_field, value_field):
    """Flatten before/after result fields into Altair-friendly rows."""
    values = []
    for category, before_key, after_key in mapping:
        values.append({category_field: category, "Period": "Before", value_field: result[before_key]})
        values.append({category_field: category, "Period": "After", value_field: result[after_key]})
    return values


# ==========================================================
# CHART COMPONENTS
# ==========================================================

def grouped_bar_chart(values, category_field, category_order, value_field, value_title, tooltip_format=".3f"):
    """Shared Before/After grouped bar chart."""
    return (
        alt.Chart(alt.Data(values=values))
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(f"{category_field}:N", title=None, sort=category_order),
            xOffset=alt.XOffset("Period:N"),
            y=alt.Y(f"{value_field}:Q", title=value_title),
            color=alt.Color(
                "Period:N",
                scale=alt.Scale(domain=["Before", "After"], range=["#5c5c66", "#2997ff"]),
                legend=alt.Legend(orient="top", title=None),
            ),
            tooltip=[
                alt.Tooltip(f"{category_field}:N"),
                alt.Tooltip("Period:N"),
                alt.Tooltip(f"{value_field}:Q", title=value_title, format=tooltip_format),
            ],
        )
        .properties(height=260)
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#86868b",
            titleColor="#86868b",
            gridColor="#1c1c1e",
            domainColor="#2c2c2e",
            tickColor="#2c2c2e",
        )
        .configure_legend(labelColor="#a1a1a6")
    )


def modern_land_cover_chart(result):
    """Before/After land-cover chart."""
    mapping = [
        ("Vegetation", "before_vegetation_km2", "after_vegetation_km2"),
        ("Built-up", "before_built_km2", "after_built_km2"),
        ("Water", "before_water_km2", "after_water_km2"),
        ("Bare", "before_bare_km2", "after_bare_km2"),
    ]
    values = _paired_values(result, mapping, "Class", "Area")
    return grouped_bar_chart(values, "Class", ["Vegetation", "Built-up", "Water", "Bare"], "Area", "Area (km²)")


def historical_index_chart(result):
    """Before/After historical spectral-index chart."""
    mapping = [
        ("NDVI", "before_mean_ndvi", "after_mean_ndvi"),
        ("MNDWI", "before_mean_mndwi", "after_mean_mndwi"),
        ("NDBI", "before_mean_ndbi", "after_mean_ndbi"),
    ]
    values = _paired_values(result, mapping, "Index", "Value")
    return grouped_bar_chart(values, "Index", ["NDVI", "MNDWI", "NDBI"], "Value", "Mean spectral index")


def trend_composition_chart(trend_data):
    """Independent per-date land-cover composition trend chart."""
    chart_rows = []

    for period in trend_data["periods"]:
        for class_name, field in [
            ("Vegetation", "vegetation_percent_of_valid_area"),
            ("Built-up", "built_percent_of_valid_area"),
            ("Water", "water_percent_of_valid_area"),
            ("Bare", "bare_percent_of_valid_area"),
        ]:
            chart_rows.append(
                {
                    "Date": period["date"],
                    "Class": class_name,
                    "Percent": period[field],
                    "Reliable": period["reliable"],
                }
            )

    base = alt.Chart(alt.Data(values=chart_rows)).encode(
        x=alt.X("Date:T", title=None),
        y=alt.Y("Percent:Q", title="Percent of that date's own valid area"),
        color=alt.Color(
            "Class:N",
            scale=alt.Scale(range=["#30d158", "#2997ff", "#0a84ff", "#98989d"]),
            legend=alt.Legend(orient="top", title=None),
        ),
    )

    line = base.mark_line(strokeWidth=2)

    points = base.mark_circle(size=90).encode(
        opacity=alt.condition(
            "datum.Reliable == true",
            alt.value(1.0),
            alt.value(0.25),
        ),
        tooltip=[
            alt.Tooltip("Date:T"),
            alt.Tooltip("Class:N"),
            alt.Tooltip("Percent:Q", format=".1f"),
            alt.Tooltip("Reliable:N"),
        ],
    )

    return (
        (line + points)
        .properties(height=320)
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#86868b",
            titleColor="#86868b",
            gridColor="#1c1c1e",
            domainColor="#2c2c2e",
            tickColor="#2c2c2e",
        )
        .configure_legend(labelColor="#a1a1a6")
    )