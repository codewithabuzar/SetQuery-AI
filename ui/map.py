"""
Interactive map building for SetQuery.
"""

import folium
import streamlit as st
from folium.plugins import Fullscreen
from streamlit_folium import st_folium


def build_study_area_map(
    latitude,
    longitude,
    radius_km,
    location_label=None,
    tile_layers=None,
    mode=None,
    allow_click_select=False,
    map_key="study_area_map",
):
    """Build an interactive geographic-context map with optional Earth Engine tile layers."""

    latitude = float(latitude)
    longitude = float(longitude)
    radius_km = float(radius_km)

    if radius_km <= 1:
        zoom_start = 15
    elif radius_km <= 2:
        zoom_start = 14
    elif radius_km <= 5:
        zoom_start = 12
    elif radius_km <= 10:
        zoom_start = 11
    else:
        zoom_start = 10

    map_object = folium.Map(
        location=[latitude, longitude],
        zoom_start=zoom_start,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
        scrollWheelZoom=False,
    )

    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="© OpenStreetMap contributors",
        name="OpenStreetMap",
        overlay=False,
        control=True,
        max_zoom=19,
    ).add_to(map_object)

    if mode == "modern_ml" and tile_layers:
        try:
            folium.TileLayer(
                tiles=tile_layers.get("before_tile_url"),
                attr="© Google Earth Engine · Sentinel-2",
                name="Before · Sentinel-2",
                overlay=True,
                control=True,
                max_zoom=19,
            ).add_to(map_object)

            folium.TileLayer(
                tiles=tile_layers.get("after_tile_url"),
                attr="© Google Earth Engine · Sentinel-2",
                name="After · Sentinel-2",
                overlay=True,
                control=True,
                max_zoom=19,
            ).add_to(map_object)

            folium.TileLayer(
                tiles=tile_layers.get("change_tile_url"),
                attr="© Google Earth Engine · Dynamic World",
                name="Change Map",
                overlay=True,
                control=True,
                max_zoom=19,
            ).add_to(map_object)

        except Exception:
            pass

    popup_text = location_label if location_label else "Selected analysis center"

    folium.CircleMarker(
        location=[latitude, longitude],
        radius=5,
        color="#f5f5f7",
        weight=2,
        fill=True,
        fill_color="#2997ff",
        fill_opacity=1,
        tooltip="Analysis center",
        popup=popup_text,
    ).add_to(map_object)

    folium.Circle(
        location=[latitude, longitude],
        radius=(radius_km * 1000),
        color="#2997ff",
        weight=2,
        opacity=0.9,
        fill=True,
        fill_color="#2997ff",
        fill_opacity=0.08,
        tooltip=f"{radius_km:g} km analysis radius",
    ).add_to(map_object)

    Fullscreen(
        position="topright",
        title="Fullscreen",
        title_cancel="Exit fullscreen",
        force_separate_button=True,
    ).add_to(map_object)

    folium.LayerControl(
        position="topright",
        collapsed=True,
    ).add_to(map_object)

    if allow_click_select:
        map_data = st_folium(
            map_object,
            height=480,
            use_container_width=True,
            returned_objects=["last_clicked"],
            key=map_key,
        )
        return map_data
    else:
        st_folium(
            map_object,
            height=480,
            use_container_width=True,
            returned_objects=[],
            key=map_key,
        )
        return None