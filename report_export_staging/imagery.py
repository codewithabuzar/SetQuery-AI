"""Satellite imagery embedding for SetQuery PDF reports."""

from io import BytesIO

import requests

from PIL import Image
from reportlab.lib.utils import ImageReader

from .formatting import BORDER, MUTED


def fetch_report_image(url, timeout=30):
    """Download an existing satellite preview safely."""

    if not url:
        return None

    response = requests.get(
        url,
        timeout=timeout,
    )

    response.raise_for_status()

    if not response.headers.get(
        "Content-Type",
        "",
    ).lower().startswith("image/"):
        raise ValueError(
            "Satellite preview URL did not return an image."
        )

    image = Image.open(
        BytesIO(response.content)
    )

    image.load()

    return image.convert("RGB")


def draw_report_image(
    pdf,
    image,
    x,
    y,
    width,
    height,
    label=None,
):
    """
    Draw an image without stretching its aspect ratio.

    The image is centered inside the available box.
    """

    pdf.setStrokeColor(BORDER)
    pdf.roundRect(
        x,
        y,
        width,
        height,
        8,
        fill=0,
        stroke=1,
    )

    if image is None:
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(
            x + width / 2,
            y + height / 2,
            "Image unavailable",
        )
        return

    image_width, image_height = image.size

    scale = min(
        width / image_width,
        height / image_height,
    )

    draw_width = image_width * scale
    draw_height = image_height * scale

    draw_x = x + (width - draw_width) / 2
    draw_y = y + (height - draw_height) / 2

    pdf.drawImage(
        ImageReader(image),
        draw_x,
        draw_y,
        width=draw_width,
        height=draw_height,
        preserveAspectRatio=True,
        mask="auto",
    )

    if label:
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(
            x,
            y - 15,
            label,
        )
