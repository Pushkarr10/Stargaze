import streamlit as st
import cv2
import numpy as np
import json
from scipy.spatial import Delaunay

# 1. THE ENHANCEMENT ENGINE
def lookup_engine_detect(img_bytes, thresh_val, min_area):
    file_bytes = np.asarray(bytearray(img_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Local Contrast (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)

    # Noise Removal
    _, thresh = cv2.threshold(enhanced, thresh_val, 255, cv2.THRESH_BINARY)
    kernel = np.ones((2,2), np.uint8)
    morphed = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    # Feature Extraction
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(morphed)
    stars = np.array([centroids[i] for i in range(1, num_labels) if min_area < stats[i, cv2.CC_STAT_AREA] < 100])
    return stars, img

# 2. THE GEOMETRIC ANALYZER
def match_and_prune(stars, db_path='lookup_db.json', tolerance=1.5):
    if len(stars) < 4: return None, None, "Insufficient stars detected."
    with open(db_path, 'r') as f:
        db = json.load(f)

    tri = Delaunay(stars)
    valid_simplices = []
    valid_point_indices = set()
    matches_found = {}

    for simplex in tri.simplices:
        p1, p2, p3 = stars[simplex]
        a, b, c = np.linalg.norm(p2-p3), np.linalg.norm(p1-p3), np.linalg.norm(p1-p2)
        try:
            ang1 = np.degrees(np.arccos(np.clip((b**2 + c**2 - a**2) / (2*b*c), -1, 1)))
            ang2 = np.degrees(np.arccos(np.clip((a**2 + c**2 - b**2) / (2*a*c), -1, 1)))
            p_tri = tuple(sorted([round(ang1, 1), round(ang2, 1), round(180-ang1-ang2, 1)]))

            for const_name, db_fp in db.items():
                for d_tri in db_fp:
                    if all(abs(p - d) < tolerance for p, d in zip(p_tri, d_tri)):
                        valid_simplices.append(simplex)
                        valid_point_indices.update(simplex)
                        matches_found[const_name] = matches_found.get(const_name, 0) + 1
                        break
        except: continue

    if not matches_found: return None, None, "No constellations recognized."
    winner = max(matches_found, key=matches_found.get)
    return winner, (valid_simplices, list(valid_point_indices)), f"Target: {winner}"

# 3. STREAMLIT UI LAYOUT
st.set_page_config(page_title="Project Lookup", layout="wide")
st.title("🛰️ Project Lookup: AI Star Tracker")

with st.sidebar:
    st.header("⚙️ Image Controls")
    t_val = st.slider("Sensitivity (Threshold)", 10, 255, 70)
    a_min = st.slider("Min Star Size (px)", 1, 10, 3)
    st.info("Increase sensitivity for faint stars; increase size to ignore noise.")

uploaded_file = st.file_uploader("Upload Star Photo", type=['jpg', 'png', 'jpeg'])

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    stars, img = lookup_engine_detect(uploaded_file.read(), t_val, a_min)
    winner, geometry, status = match_and_prune(stars)

    with col1:
        st.write("### Raw Detection")
        # Visual feedback of ALL detected points
        raw_preview = img.copy()
        for x, y in stars:
            cv2.circle(raw_preview, (int(x), int(y)), 5, (255, 0, 0), -1)
        st.image(cv2.cvtColor(raw_preview, cv2.COLOR_BGR2RGB), use_container_width=True)

    with col2:
        st.write("### Identified Pattern")
        if winner:
            st.success(status)
            valid_simplices, valid_indices = geometry
            overlay = img.copy()
            for simplex in valid_simplices:
                cv2.polylines(overlay, [stars[simplex].astype(int)], True, (255, 255, 0), 2)
            for idx in valid_indices:
                cv2.circle(overlay, (int(stars[idx][0]), int(stars[idx][1])), 8, (0, 255, 0), -1)
            st.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB), use_container_width=True)
        else:
            st.error(status)
