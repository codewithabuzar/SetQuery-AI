"""Static geographic reference map for SetQuery PDF reports."""

from io import BytesIO
from math import atan, exp, log, pi, radians, sinh, tan

import requests
from PIL import Image, ImageDraw, ImageFont


TILE_SIZE = 256
MAP_SIZE = 768

OSM_TILE_URL = (
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
)


def _latlon_to_pixel(lat, lon, zoom):
    """Convert geographic coordinates to Web Mercator pixels."""

    lat = max(-85.05112878, min(85.05112878, float(lat)))
    lon = float(lon)

    scale = TILE_SIZE * (2 ** zoom)

    x = (lon + 180.0) / 360.0 * scale

    latitude_radians = radians(lat)

    y = (
        1.0
        - log(
            tan(latitude_radians)
            + 1.0 / __import__("math").cos(latitude_radians)
        ) / pi
    ) / 2.0 * scale

    return x, y


def _choose_zoom(radius_km):
    if radius_km <= 1:
        return 13
    if radius_km <= 2:
        return 12
    if radius_km <= 5:
        return 11
    if radius_km <= 10:
        return 10
    return 9


def build_reference_map(latitude, longitude, radius_km):
    """
    Generate a static reference map using OpenStreetMap tiles.

    Used only for PDF generation.
    """

    latitude = float(latitude)
    longitude = float(longitude)
    radius_km = float(radius_km)

    zoom = _choose_zoom(radius_km)

    center_x, center_y = _latlon_to_pixel(
        latitude,
        longitude,
        zoom,
    )

    image = Image.new(
        "RGB",
        (MAP_SIZE, MAP_SIZE),
        "#F3F4F6",
    )

    left = center_x - MAP_SIZE / 2
    top = center_y - MAP_SIZE / 2

    first_x = int(left // TILE_SIZE)
    first_y = int(top // TILE_SIZE)

    last_x = int((left + MAP_SIZE) // TILE_SIZE)
    last_y = int((top + MAP_SIZE) // TILE_SIZE)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "SetQuery-AI/1.0 (research report map)"
    })

    loaded_tiles = 0

    for tile_x in range(first_x, last_x + 1):
        for tile_y in range(first_y, last_y + 1):

            max_tile = 2 ** zoom

            if not 0 <= tile_y < max_tile:
                continue

            wrapped_x = tile_x % max_tile

            url = OSM_TILE_URL.format(
                z=zoom,
                x=wrapped_x,
                y=tile_y,
            )

            try:
                response = session.get(url, timeout=12)
                response.raise_for_status()

                tile = Image.open(
                    BytesIO(response.content)
                ).convert("RGB")

                paste_x = int(tile_x * TILE_SIZE - left)
                paste_y = int(tile_y * TILE_SIZE - top)

                image.paste(tile, (paste_x, paste_y))
                loaded_tiles += 1

            except Exception:
                continue

    if loaded_tiles == 0:
        raise RuntimeError(
            "Reference map tiles could not be downloaded."
        )

    draw = ImageDraw.Draw(image, "RGBA")

    center = MAP_SIZE / 2

    # Approximate Web Mercator ground resolution.
    metres_per_pixel = (
        156543.03392
        * __import__("math").cos(radians(latitude))
        / (2 ** zoom)
    )

    radius_pixels = (
        radius_km * 1000 / metres_per_pixel
    )

    draw.ellipse(
        (
            center - radius_pixels,
            center - radius_pixels,
            center + radius_pixels,
            center + radius_pixels,
        ),
        fill=(41, 151, 255, 35),
        outline=(41, 151, 255, 230),
        width=4,
    )

    draw.ellipse(
        (
            center - 9,
            center - 9,
            center + 9,
            center + 9,
        ),
        fill=(41, 151, 255, 255),
        outline=(255, 255, 255, 255),
        width=3,
    )

    # Attribution required by OpenStreetMap.
    draw.rectangle(
        (0, MAP_SIZE - 30, MAP_SIZE, MAP_SIZE),
        fill=(255, 255, 255, 225),
    )

    draw.text(
        (12, MAP_SIZE - 22),
        "Map data: OpenStreetMap contributors",
        fill=(30, 41, 59, 255),
    )

    return image
