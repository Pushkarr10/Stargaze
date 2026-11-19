import os
import cv2
import numpy as np
from scipy.spatial import Delaunay
import json
import math
from typing import List, Tuple, Dict

# Load constellation database relative to repository root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# engine.py is in core/, so go up one level to repo root
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
DATA_PATH = os.path.join(REPO_ROOT, 'data', 'stars_db.json')

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    stars_db = json.load(f)

_CONSTELLATION_DB = stars_db['constellations']


def _apply_clahe(img_gray: np.ndarray, clip_limit: float = 3.0, tile_grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
    """Apply CLAHE to enhance contrast of a grayscale image."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(img_gray)


def extract_stars(
    img: np.ndarray,
    thresh_val: int = 70,
    min_area: int = 3,
    max_area: int = 100,
) -> np.ndarray:
    """Return an (N, 2) array of star centroids extracted from an RGB image.

    Steps:
    1. Convert to grayscale.
    2. Apply CLAHE.
    3. Binary threshold.
    4. 2×2 morphological opening to remove noise.
    5. Connected components – filter by area.
    """
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img
    enhanced = _apply_clahe(gray)
    _, binary = cv2.threshold(enhanced, thresh_val, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    # Connected components with stats gives centroid in (x, y)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(opened, connectivity=8)
    # Filter out background label 0 and by area
    keep = []
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if min_area <= area <= max_area:
            keep.append(centroids[i])
    if not keep:
        return np.empty((0, 2))
    return np.array(keep)


def triangulate(centroids: np.ndarray) -> np.ndarray:
    """Return Delaunay simplices (triangles) as an (M, 3) index array.
    If fewer than 3 points are provided, returns an empty array.
    """
    if len(centroids) < 3:
        return np.empty((0, 3), dtype=int)
    delaunay = Delaunay(centroids)
    return delaunay.simplices


def _angle_from_vectors(a: np.ndarray, b: np.ndarray) -> float:
    """Return interior angle (degrees) between two vectors using the law of cosines."""
    dot = np.dot(a, b)
    norm_prod = np.linalg.norm(a) * np.linalg.norm(b)
    cos_theta = np.clip(dot / (norm_prod + 1e-12), -1.0, 1.0)
    return math.degrees(math.acos(cos_theta))


def triangle_angles(triangle: np.ndarray) -> Tuple[float, float, float]:
    """Given three points (3,2), compute the three interior angles (sorted ascending).
    Returns a tuple of angles rounded to 1 decimal place.
    """
    p0, p1, p2 = triangle
    a = p1 - p0
    b = p2 - p0
    c = p2 - p1
    ang0 = _angle_from_vectors(a, b)
    ang1 = _angle_from_vectors(-a, c)
    ang2 = _angle_from_vectors(-b, -c)
    angles = [round(ang0, 1), round(ang1, 1), round(ang2, 1)]
    angles.sort()
    return tuple(angles)  # type: ignore


def match_constellations(
    barcodes: List[Tuple[float, float, float]],
    db: List[Dict] = None,
    tolerance: float = 1.5,
) -> Tuple[str, int, List[int]]:
    """Fuzzy‑match a list of triangle barcodes against the constellation database.

    Returns:
    - matched constellation name (or empty string if none)
    - confidence score (number of matching triangles)
    - list of indices of barcodes that contributed to the match
    """
    if db is None:
        db = _CONSTELLATION_DB
    votes: Dict[str, List[int]] = {c['name']: [] for c in db}
    for idx, barcode in enumerate(barcodes):
        for const in db:
            for ref in const['barcodes']:
                if all(abs(b - r) <= tolerance for b, r in zip(barcode, ref)):
                    votes[const['name']].append(idx)
                    break
    winner = ''
    best_score = 0
    matched_idxs: List[int] = []
    for name, idxs in votes.items():
        if len(idxs) > best_score:
            winner = name
            best_score = len(idxs)
            matched_idxs = idxs
    return winner, best_score, matched_idxs
