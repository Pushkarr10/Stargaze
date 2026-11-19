import os
import io
import json
import base64
from datetime import datetime, time
import pytz
import cv2
import numpy as np
from PIL import Image
import streamlit as st
import folium
from streamlit_folium import st_folium

from core.engine import extract_stars, triangulate, triangle_angles, match_constellations
from core.synthetic import generate_constellation_image
import stargaze_utils as star_logic

# =================================================================
# 🌌 BASE CONFIG & ASSET LOADER
# =================================================================

st.set_page_config(
    layout="wide",
    page_title="Stargaze | Cosmic Observatory & Sky-Dex",
    page_icon="🔭",
    initial_sidebar_state="expanded"
)

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(REPO_ROOT, "data", "stars_db.json")

def get_base64_image(filename):
    for possible_path in [
        os.path.join(REPO_ROOT, filename),
        os.path.join(REPO_ROOT, "assets", filename)
    ]:
        if os.path.exists(possible_path):
            with open(possible_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""

DASHBOARD_BG = get_base64_image("dashboard_bg.png") or get_base64_image("neon_horizon.png")

# Load database
with open(DATA_PATH, "r", encoding="utf-8") as f:
    DB = json.load(f)

# =================================================================
# 🧬 SESSION STATE INITIALIZATION
# =================================================================

if "collected" not in st.session_state:
    st.session_state.collected = {"Orion": True}  # Initial starter constellation unlocked

if "active_mode" not in st.session_state:
    st.session_state.active_mode = "🌌 Observatory Hub"

if "lat" not in st.session_state:
    st.session_state.lat = 18.5204
if "lon" not in st.session_state:
    st.session_state.lon = 73.8567

IST = pytz.timezone("Asia/Kolkata")
if "sim_date" not in st.session_state:
    st.session_state.sim_date = datetime.now(IST).date()
if "sim_time" not in st.session_state:
    now_ist = datetime.now(IST)
    st.session_state.sim_time = time(now_ist.hour, now_ist.minute)

def reset_to_now():
    now_ist = datetime.now(IST)
    st.session_state.sim_date = now_ist.date()
    st.session_state.sim_time = time(now_ist.hour, now_ist.minute)

def authenticate_image(uploaded_file):
    if uploaded_file is None:
        return False, "No signal detected."
    if uploaded_file.size > 15 * 1024 * 1024:
        return False, "Signal too strong (File > 15MB). Please compress."
    return True, "Signal locked. Telemetry received."

# =================================================================
# 🎨 ZONE: CELESTIAL STYLING & GLASSO-MORPHISM
# =================================================================

def inject_cosmic_theme():
    bg_style = ""
    if DASHBOARD_BG:
        bg_style = f"""
            background:
                linear-gradient(180deg, rgba(5, 7, 20, 0.88) 0%, rgba(2, 4, 12, 0.96) 100%),
                url("data:image/png;base64,{DASHBOARD_BG}");
            background-attachment: fixed;
            background-size: cover;
            background-position: center;
        """
    else:
        bg_style = """
            background: radial-gradient(circle at 50% 20%, #0d1b3e 0%, #060b1c 50%, #02040a 100%);
        """

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lobster&family=Inter:wght@300;400;600;700&display=swap');

    .stApp {{
        {bg_style}
        color: #e2e8f0;
    }}

    .sky-header {{
        background: linear-gradient(180deg, rgba(2, 4, 15, 0.95) 0%, rgba(10, 20, 50, 0.85) 65%, rgba(15, 30, 75, 0.7) 100%);
        padding: 35px 15px 25px 15px;
        text-align: center;
        border-bottom: 1px solid rgba(74, 144, 226, 0.35);
        border-radius: 0 0 35px 35px;
        margin-bottom: 25px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(10px);
    }}

    .sparkle-title {{
        font-family: 'Lobster', cursive !important;
        font-size: clamp(2.8rem, 6vw, 4.4rem) !important;
        color: #ffffff !important;
        text-shadow: 0 0 12px #fff, 0 0 25px #4A90E2, 0 0 45px #00d2ff;
        animation: title-glow 3s ease-in-out infinite alternate;
        margin: 0;
        line-height: 1.1;
    }}

    @keyframes title-glow {{
        from {{ text-shadow: 0 0 10px #fff, 0 0 22px #4A90E2; opacity: 0.92; }}
        to {{ text-shadow: 0 0 25px #fff, 0 0 38px #4A90E2, 0 0 55px #00d2ff; opacity: 1; }}
    }}

    .glass-pane {{
        background: rgba(14, 20, 42, 0.65);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(74, 144, 226, 0.22);
        border-radius: 20px;
        padding: 24px;
        text-align: center;
        height: 100%;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }}
    
    .glass-pane:hover {{
        transform: translateY(-5px);
        border: 1px solid rgba(0, 210, 255, 0.6);
        box-shadow: 0 12px 30px rgba(0, 210, 255, 0.2);
    }}

    .rarity-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    .rarity-legendary {{ background: rgba(255, 180, 0, 0.2); color: #ffc107; border: 1px solid #ffc107; }}
    .rarity-rare {{ background: rgba(0, 229, 255, 0.2); color: #00e5ff; border: 1px solid #00e5ff; }}
    .rarity-uncommon {{ background: rgba(179, 136, 255, 0.2); color: #b388ff; border: 1px solid #b388ff; }}
    .rarity-common {{ background: rgba(100, 255, 218, 0.2); color: #64ffda; border: 1px solid #64ffda; }}

    .stButton>button {{
        background: linear-gradient(135deg, #0b3d91 0%, #1e5bb8 100%);
        color: #ffffff;
        border-radius: 12px;
        border: 1px solid rgba(74, 144, 226, 0.4);
        padding: 8px 20px;
        font-weight: 600;
        transition: all 0.25s ease;
    }}
    .stButton>button:hover {{
        background: linear-gradient(135deg, #1e5bb8 0%, #00d2ff 100%);
        border-color: #00d2ff;
        box-shadow: 0 0 18px rgba(0, 210, 255, 0.45);
        color: #ffffff;
    }}

    div[data-testid="stExpander"] {{
        background: rgba(10, 16, 35, 0.7);
        border: 1px solid rgba(74, 144, 226, 0.25);
        border-radius: 16px;
        margin-bottom: 15px;
    }}

    h1, h2, h3, h4, h5, p, label {{
        font-family: 'Inter', sans-serif !important;
    }}
    </style>

    <div class="sky-header">
        <h1 class="sparkle-title">Stargaze</h1>
        <p style="font-family: 'Inter', sans-serif; letter-spacing: 4px; font-size: 0.82rem; text-transform: uppercase; color: #94a3b8; margin-top: 8px;">
            ✦ THE CELESTIAL OBSERVATORY & SKY-DEX ✦
        </p>
    </div>
    """, unsafe_allow_html=True)

inject_cosmic_theme()

# =================================================================
# 🧭 OBSERVATORY CALIBRATION SELECTOR
# =================================================================

MODES = [
    "🌌 Observatory Hub",
    "🔭 Deep Space Scanner",
    "🪐 Live Planetarium",
    "✨ The Cosmic Archive"
]

selected_mode = st.select_slider(
    "Observatory Mode Calibration",
    options=MODES,
    value=st.session_state.active_mode,
    label_visibility="collapsed"
)
st.session_state.active_mode = selected_mode

# =================================================================
# 🌌 ZONE 1: OBSERVATORY HUB (Neutral Overview)
# =================================================================

if st.session_state.active_mode == "🌌 Observatory Hub":
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.markdown("""
            <div class="glass-pane">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">📐</div>
                <h3 style="color:#00d2ff; font-size: 1.35rem; margin-bottom: 8px;">Deep Space Scanner</h3>
                <p style="opacity: 0.82; font-size: 0.88rem; line-height: 1.5;">
                    Isolate star centroids with CLAHE computer vision, form Delaunay triangulation meshes,
                    and compute invariant triangle angle barcodes.
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Launch Scanner 🔭", use_container_width=True):
            st.session_state.active_mode = "🔭 Deep Space Scanner"
            st.rerun()

    with col_b:
        st.markdown("""
            <div class="glass-pane">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">🪐</div>
                <h3 style="color:#4A90E2; font-size: 1.35rem; margin-bottom: 8px;">Live Planetarium</h3>
                <p style="opacity: 0.82; font-size: 0.88rem; line-height: 1.5;">
                    Simulate the celestial sphere in full 3D immersion or 2D polar projection.
                    Tap the interactive world map to observe constellations from any coordinate on Earth.
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Planetarium 🪐", use_container_width=True):
            st.session_state.active_mode = "🪐 Live Planetarium"
            st.rerun()

    with col_c:
        st.markdown("""
            <div class="glass-pane">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">✨</div>
                <h3 style="color:#ffc107; font-size: 1.35rem; margin-bottom: 8px;">The Cosmic Archive</h3>
                <p style="opacity: 0.82; font-size: 0.88rem; line-height: 1.5;">
                    Your permanent Sky-Dex collection log. Unearth ancient mythology, brightest stars,
                    viewing seasons, and rare celestial tier rewards.
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Sky-Dex ✨", use_container_width=True):
            st.session_state.active_mode = "✨ The Cosmic Archive"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Observatory Status Telemetry
    total_db = len(DB['constellations'])
    collected_count = len(st.session_state.collected)
    
    with st.container():
        st.markdown("### 📡 Observatory Telemetry & Calibration Status")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Cataloged Stars", "5,020", "Hipparcos")
        m2.metric("Constellations in Dex", f"{collected_count} / {total_db}", f"{(collected_count/total_db)*100:.0f}% Unlocked")
        m3.metric("Observer Latitude", f"{st.session_state.lat:.2f}° N")
        m4.metric("Observer Longitude", f"{st.session_state.lon:.2f}° E")

# =================================================================
# 🔭 ZONE 2: DEEP SPACE SCANNER (Science & Pattern Recognition)
# =================================================================

elif st.session_state.active_mode == "🔭 Deep Space Scanner":
    st.markdown("<h2 style='text-align:center; color:#00d2ff;'>🔭 Deep Space Pattern Scanner</h2>", unsafe_allow_html=True)
    st.caption("Perform CLAHE contrast enhancement, star centroid extraction, Delaunay triangulation, and invariant angle barcode matching.")

    with st.sidebar:
        st.subheader("🛠️ CV Scanner Calibration")
        thresh_val = st.slider("Sensitivity (Threshold)", 10, 255, 70, help="Lower values detect dimmer stars; higher values isolate brighter stars.")
        min_area = st.slider("Min Star Area (px)", 1, 15, 3)
        max_area = st.slider("Max Star Area (px)", 20, 200, 100)
        angle_tolerance = st.slider("Angle Tolerance (°)", 0.5, 3.0, 1.5, step=0.1, help="Max angular deviation for barcode matching.")
        
        st.markdown("---")
        st.subheader("✨ Synthetic Sky Generator")
        sample_consts = [c['name'] for c in DB['constellations']]
        sample_choice = st.selectbox("Select Constellation to Simulate", sample_consts)
        gen_sample = st.button("Generate Synthetic Capture", use_container_width=True)

    uploaded_file = st.file_uploader("Upload Night Sky Capture", type=['png', 'jpg', 'jpeg'])

    if gen_sample:
        synthetic_img = generate_constellation_image(sample_choice)
        buf = io.BytesIO()
        synthetic_img.save(buf, format='PNG')
        buf.seek(0)
        uploaded_file = buf
        st.success(f"Generated synthetic sky capture with exact geometric pattern for **{sample_choice}**!")

    if uploaded_file is not None:
        valid, msg = authenticate_image(uploaded_file)
        if not valid:
            st.error(msg)
        else:
            image = Image.open(uploaded_file).convert('RGB')
            img_np = np.array(image)

            with st.spinner("Executing CV pipeline & Delaunay triangulation..."):
                centroids = extract_stars(img_np, thresh_val=thresh_val, min_area=min_area, max_area=max_area)
                simplices = triangulate(centroids)
                barcodes = [triangle_angles(centroids[s]) for s in simplices]
                match_name, confidence, matched_idxs = match_constellations(
                    barcodes, 
                    DB['constellations'], 
                    tolerance=angle_tolerance
                )

            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("1. Star Centroid Detection")
                det_img = img_np.copy()
                for (x, y) in centroids:
                    cv2.circle(det_img, (int(x), int(y)), 4, (0, 255, 255), -1)
                st.image(det_img, caption=f"Extracted {len(centroids)} Star Centroids", use_container_width=True)

            with col2:
                st.subheader("2. Delaunay Mesh & Pattern Match")
                pat_cv = img_np.copy()
                for simplex in simplices:
                    pts = centroids[simplex].astype(int)
                    cv2.polylines(pat_cv, [pts], isClosed=True, color=(50, 60, 160), thickness=1)

                for idx in matched_idxs:
                    simplex = simplices[idx]
                    pts = centroids[simplex].astype(int)
                    cv2.polylines(pat_cv, [pts], isClosed=True, color=(0, 255, 255), thickness=3)
                    for (x, y) in pts:
                        cv2.circle(pat_cv, (int(x), int(y)), 5, (0, 255, 120), -1)

                st.image(pat_cv, caption=f"Triangles: {len(simplices)} | Matched Barcodes: {len(matched_idxs)}", use_container_width=True)

            st.markdown("---")
            res_c1, res_c2 = st.columns([2, 1])

            with res_c1:
                if match_name:
                    st.success(f"### 🪐 Target Constellation Identified: **{match_name}**")
                    target_meta = next((c for c in DB['constellations'] if c['name'] == match_name), None)
                    if target_meta:
                        meta = target_meta['metadata']
                        st.markdown(f"""
                        * **Brightest Star:** `{meta.get('brightest_star')}`
                        * **Season:** `{meta.get('season')}`
                        * **Rarity Tier:** `{meta.get('rarity')}`
                        * **Mythological Lore:** *{meta.get('lore')}*
                        """)
                else:
                    st.warning("### ⚠️ Pattern Unresolved: Unknown Constellation")
                    st.info("Try tuning the sensitivity threshold or angle tolerance in the sidebar.")

            with res_c2:
                if match_name:
                    is_already = match_name in st.session_state.collected
                    if is_already:
                        st.info(f"✨ **{match_name}** is already in your Sky-Dex!")
                    else:
                        if st.button("⭐ Claim & Add to Sky-Dex", use_container_width=True):
                            st.session_state.collected[match_name] = True
                            st.balloons()
                            st.rerun()

# =================================================================
# 🪐 ZONE 3: LIVE PLANETARIUM (3D & 2D Sky Simulation)
# =================================================================

elif st.session_state.active_mode == "🪐 Live Planetarium":
    st.markdown("<h2 style='text-align:center; color:#4A90E2;'>🪐 Live Celestial Planetarium</h2>", unsafe_allow_html=True)
    st.caption("Observe real-time or simulated celestial coordinates computed via Skyfield ephemeris with 5,000+ stars.")

    # Location & Time Settings
    with st.expander("⚙️ Location & Temporal Calibration", expanded=True):
        col_map, col_time = st.columns([1, 1])
        
        with col_map:
            st.write("**Click the world map to set observer coordinates:**")
            m = folium.Map(
                location=[st.session_state.lat, st.session_state.lon], 
                zoom_start=3, 
                tiles="CartoDB dark_matter"
            )
            folium.Marker(
                [st.session_state.lat, st.session_state.lon],
                popup="Observer Station",
                icon=folium.Icon(color="blue", icon="eye")
            ).add_to(m)
            m.add_child(folium.LatLngPopup())
            map_data = st_folium(m, height=240, width="100%", key="planetarium_map")
            
            if map_data and map_data.get('last_clicked'):
                st.session_state.lat = map_data['last_clicked']['lat']
                st.session_state.lon = map_data['last_clicked']['lng']

            st.caption(f"Coordinates: **{st.session_state.lat:.4f}° N, {st.session_state.lon:.4f}° E**")

        with col_time:
            st.write("**Date & Time Settings (IST):**")
            d_col, n_col = st.columns([3, 1])
            with d_col:
                st.date_input("Observation Date", key="sim_date")
            with n_col:
                st.button("↺ Now", on_click=reset_to_now, help="Sync to current real-time IST")

            st.slider(
                "Time of Night (IST)",
                min_value=time(0, 0),
                max_value=time(23, 59),
                format="HH:mm",
                key="sim_time"
            )
            show_const_lines = st.toggle("Overlay Constellation Stick Figures", value=True)

    # Calculate celestial positions
    user_datetime_naive = datetime.combine(st.session_state.sim_date, st.session_state.sim_time)
    user_datetime_ist = IST.localize(user_datetime_naive)
    observer_time_utc = user_datetime_ist.astimezone(pytz.utc)

    st.caption(f"🔭 Observing Sky at **{user_datetime_ist.strftime('%d %b %Y, %H:%M')} IST** | Physics calculation: `{observer_time_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC`")

    with st.spinner("Aligning celestial sphere & ephemeris..."):
        df_stars = star_logic.load_star_data()
        visible_stars = star_logic.calculate_sky_positions(
            df_stars, 
            st.session_state.lat, 
            st.session_state.lon, 
            observer_time_utc
        )

    tab_3d, tab_2d = st.tabs(["🪐 3D Celestial Immersion", "🗺️ 2D Polar Star Chart"])

    with tab_3d:
        st.caption("Rotate, pan, and tilt inside the 3D celestial sphere. The ground terrain mesh represents the horizon.")
        fig_3d = star_logic.create_3d_sphere_chart(
            visible_stars, 
            show_constellations=show_const_lines
        )
        st.plotly_chart(fig_3d, use_container_width=True)

    with tab_2d:
        st.caption("Zenith-centered polar projection of all stars above the observer's local horizon.")
        fig_2d = star_logic.create_star_chart(visible_stars)
        st.plotly_chart(fig_2d, use_container_width=True)

# =================================================================
# ✨ ZONE 4: THE COSMIC ARCHIVE (Sky-Dex Collection)
# =================================================================

elif st.session_state.active_mode == "✨ The Cosmic Archive":
    total_consts = len(DB['constellations'])
    collected_consts = len(st.session_state.collected)
    ratio = collected_consts / total_consts

    st.markdown("<h2 style='text-align:center; color:#ffc107;'>✨ The Cosmic Archive (Sky-Dex)</h2>", unsafe_allow_html=True)
    st.progress(ratio)
    st.markdown(f"<p style='text-align:center; font-weight:600;'>{collected_consts} of {total_consts} Constellations Documented ({ratio*100:.0f}%)</p>", unsafe_allow_html=True)

    # Action bar
    d_col1, d_col2 = st.columns([3, 1])
    with d_col1:
        progress_data = {
            "unlocked": list(st.session_state.collected.keys()),
            "last_updated": datetime.now(pytz.utc).isoformat(),
            "station_coordinates": [st.session_state.lat, st.session_state.lon]
        }
        st.download_button(
            "📥 Export Sky-Dex Archive (JSON)",
            data=json.dumps(progress_data, indent=2),
            file_name="skydex_archive.json",
            mime="application/json"
        )
    with d_col2:
        if st.button("Reset Collection Log"):
            st.session_state.collected = {}
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    cols = st.columns(3)
    for idx, const in enumerate(DB['constellations']):
        name = const['name']
        meta = const['metadata']
        is_unlocked = name in st.session_state.collected
        rarity = meta.get('rarity', 'Common')
        rarity_class = f"rarity-{rarity.lower()}"

        col = cols[idx % 3]
        with col:
            if is_unlocked:
                st.markdown(f"""
                <div class="glass-pane" style="border-color: rgba(255, 193, 7, 0.4);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <h3 style="color:#ffffff; margin:0; font-size:1.4rem;">{name}</h3>
                        <span class="rarity-badge {rarity_class}">{rarity}</span>
                    </div>
                    <p style="color:#00d2ff; font-weight:600; font-size:0.9rem; margin-bottom:4px;">
                        ⭐ Brightest: {meta.get('brightest_star')} | 🍂 {meta.get('season')}
                    </p>
                    <p style="opacity:0.85; font-size:0.86rem; line-height:1.4; margin-top:8px;">
                        "{meta.get('lore')}"
                    </p>
                    <div style="margin-top:12px; font-size:0.75rem; color:#64ffda; text-transform:uppercase; letter-spacing:1px; font-weight:700;">
                        ✓ Documented in Archive
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="glass-pane" style="opacity: 0.55; border-style: dashed;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <h3 style="color:#94a3b8; margin:0; font-size:1.4rem;">??? {name}</h3>
                        <span class="rarity-badge {rarity_class}">{rarity}</span>
                    </div>
                    <p style="color:#64748b; font-size:0.9rem;">Coordinates Encrypted</p>
                    <p style="opacity:0.7; font-size:0.84rem; line-height:1.4;">
                        Undiscovered pattern. Scan the night sky or generate a synthetic capture to unlock telemetry.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
