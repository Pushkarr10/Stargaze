import numpy as np
import random
from PIL import Image, ImageDraw
import json
import math
from typing import Tuple

# Load the same DB as the engine (relative to repository root)
import os
# Load constellation database relative to repository root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
DATA_PATH = os.path.join(REPO_ROOT, 'data', 'stars_db.json')
with open(DATA_PATH, 'r', encoding='utf-8') as f:
    _DB = json.load(f)['constellations']

# Duplicate DB load removed


def _points_from_angles(angle_triplet: Tuple[float, float, float], scale: float = 50.0) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
    """Create three points forming a triangle with the given interior angles.
    The first point is placed at (0, 0), the second on the positive X axis at (scale, 0).
    The third point is computed using the law of cosines to satisfy the angle at the first vertex.
    Returns coordinates as (x, y) tuples.
    """
    a1, a2, a3 = angle_triplet  # sorted ascending but we just need any order; we treat a1 as angle at point 0
    # Using side lengths: let side opposite a1 be length c (between points 1 and 2)
    c = scale
    # Choose arbitrary side lengths a and b using law of sines with a chosen circumradius
    # Simplify: set side a (between points 0 and 2) = scale, compute point 2 using angle a1.
    # Place point0 at (0,0), point1 at (c,0).
    # Compute location of point2 using angle a1 at point0.
    rad = math.radians(a1)
    x2 = scale * math.cos(rad)
    y2 = scale * math.sin(rad)
    return (0.0, 0.0), (c, 0.0), (x2, y2)


def _draw_triangle(draw: ImageDraw.Draw, pts: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]], offset: Tuple[float, float], radius: int = 2, color: Tuple[int, int, int] = (255, 255, 255)):
    """Draw the three vertices of a triangle on the image, applying an offset.
    """
    ox, oy = offset
    for (x, y) in pts:
        cx = int(x + ox)
        cy = int(y + oy)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)


def generate_constellation_image(constellation_name: str, img_size: int = 512, star_noise: int = 300) -> Image.Image:
    """Generate a synthetic night‑sky image containing the given constellation.

    Parameters
    ----------
    constellation_name: Name of the constellation as stored in ``stars_db.json``.
    img_size: Width and height of the square image in pixels.
    star_noise: Number of random background stars to sprinkle.

    Returns
    -------
    Pillow ``Image`` object.
    """
    # Create black background
    img = Image.new('RGB', (img_size, img_size), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Add random background stars (small white dots)
    for _ in range(star_noise):
        x = random.randint(0, img_size - 1)
        y = random.randint(0, img_size - 1)
        brightness = random.randint(150, 255)
        draw.point((x, y), fill=(brightness, brightness, brightness))

    # Find constellation entry
    const = next((c for c in _DB if c['name'].lower() == constellation_name.lower()), None)
    if not const:
        raise ValueError(f"Constellation '{constellation_name}' not found in database.")

    # Determine a random offset so the constellation appears somewhere within the canvas
    max_offset = img_size - 100  # leave margin
    offset_x = random.randint(20, max_offset)
    offset_y = random.randint(20, max_offset)

    # Draw each barcode (triangle) as three stars
    for barcode in const['barcodes']:
        pts = _points_from_angles(tuple(barcode), scale=40.0)
        _draw_triangle(draw, pts, (offset_x, offset_y), radius=3, color=(255, 255, 200))

    return img
