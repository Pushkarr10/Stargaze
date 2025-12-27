import streamlit as st
import cv2
import numpy as np
import json
import bcrypt
import re
from scipy.spatial import Delaunay
from supabase import create_client, Client

# =================================================================
# 🧬 ZONE 1: THE BACKBONE (Geometric Engine)
# =================================================================

def stargaze_engine(img_bytes, thresh_val, min_area):
    file_bytes = np.asarray(bytearray(img_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    _, thresh = cv2.threshold(enhanced, thresh_val, 255, cv2.THRESH_BINARY)
    morphed = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((2,2), np.uint8))
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(morphed)
    stars = np.array([centroids[i] for i in range(1, num_labels) if min_area < stats[i, cv2.CC_STAT_AREA] < 100])
    return stars, img

def match_patterns(stars, db_path='lookup_db.json'):
    try:
        with open(db_path, 'r') as f:
            db = json.load(f)
    except: return None, None, "Database not found."
    if len(stars) < 4: return None, None, "Need more stars."
    
    tri = Delaunay(stars)
    matches = {}
    valid_simplices = []
    for simplex in tri.simplices:
        p1, p2, p3 = stars[simplex]
        side_lens = sorted([np.linalg.norm(p1-p2), np.linalg.norm(p2-p3), np.linalg.norm(p3-p1)])
        barcode = [round(side_lens[0]/side_lens[2], 2), round(side_lens[1]/side_lens[2], 2)]
        for name, fingerprints in db.items():
            for fp in fingerprints:
                if all(abs(b - f) < 0.05 for b, f in zip(barcode, fp)):
                    matches[name] = matches.get(name, 0) + 1
                    valid_simplices.append(simplex)
    
    if not matches: return None, None, "No patterns recognized."
    return max(matches, key=matches.get), valid_simplices, "Success!"

# =================================================================
# 🧠 ZONE 2: THE BRAIN (Database & Security)
# =================================================================

supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def hash_pass(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def check_pass(p, h): return bcrypt.checkpw(p.encode(), h.encode())
def is_valid_email(email): return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

# =================================================================
# 🎨 ZONE 3: THE INTERFACE (User Experience)
# =================================================================
# =================================================================
# 🎨 ZONE 3: THE INTERFACE (The Celestial Sanctuary)
# =================================================================
# =================================================================
# 🎨 ZONE 3: THE INTERFACE (The Celestial Sanctuary)
# =================================================================

# 3.1: THE DIALOG (Onboarding)
@st.dialog("Welcome to the Observatory! 🔭")
def welcome_popup():
    st.markdown("""
    ### Heyy Great To Have You Onboard! 🌌
    Welcome to **Stargaze**. This is the start to your sparkling experience ✨✨✨.
    
    **Your Journey:**
    - Slide the Lens **LEFT** for the Science Hub 🔬
    - Slide the Lens **RIGHT** for the Creative Gallery 🎨
    """)
    if st.button("Let's Start Mapping!"):
        st.session_state.has_seen_intro = True
        st.rerun()

# 3.2: THE CSS VAULT (Visual Identity & Layout)
# We use your cosmic image with a three-point gradient for the spotlight effect.
st.set_page_config(page_title="Stargaze", page_icon="🌌", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lobster&family=Inter:wght@400;700&family=Shadows+Into+Light&display=swap');

    /* BACKGROUND: Cosmic Image + Spotlight Gradient */
    .stApp {
        background: 
            linear-gradient(90deg, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.2) 50%, rgba(0,0,0,0.9) 100%),
            url("https://raw.githubusercontent.com/Pushkar-Stargaze/assets/main/cosmic_bg.jpg");
        background-attachment: fixed;
        background-size: cover;
    }

    /* HEADER: Sparkle Title & Shooting Stars */
    .sky-header {
        background: linear-gradient(180deg, #000000 0%, #060b26 70%, #0c1445 100%);
        padding: 40px 10px;
        text-align: center;
        border-bottom: 3px solid #4A90E2;
        border-radius: 0 0 40px 40px;
        margin-bottom: 30px;
        position: relative;
    }

    .sparkle-title {
        font-family: 'Lobster', cursive !important;
        font-size: clamp(2.5rem, 8vw, 5rem) !important; 
        color: white !important;
        text-shadow: 0 0 10px #fff, 0 0 20px #4A90E2;
        animation: title-glow 2s ease-in-out infinite alternate;
        white-space: nowrap;
    }
    @keyframes title-glow {
        from { text-shadow: 0 0 10px #fff; }
        to { text-shadow: 0 0 25px #fff, 0 0 40px #4A90E2; }
    }

    /* THE MODERN ORB SLIDER */
    div[data-baseweb="slider"] {
        background: rgba(255, 255, 255, 0.1) !important;
        height: 14px !important;
        border-radius: 20px !important;
    }
    div[role="slider"] {
        background: radial-gradient(circle, #ffffff 0%, #4A90E2 100%) !important;
        border: 2px solid white !important;
        box-shadow: 0 0 18px #4A90E2 !important;
        width: 28px !important;
        height: 28px !important;
    }

    /* THE ASYMMETRIC TORN PORTAL */
    .tear-wrapper {
        display: flex;
        width: 100%;
        min-height: 520px;
        position: relative;
        filter: drop-shadow(0px 15px 35px rgba(0,0,0,0.8));
    }

    .wing-science {
        flex: 1;
        background-color: #f4e4bc;
        background-image: radial-gradient(rgba(0,0,0,0.1) 1px, transparent 1px);
        background-size: 25px 25px;
        padding: 45px;
        color: #1a1a1a;
        clip-path: polygon(0% 0%, 96% 0%, 100% 15%, 92% 30%, 100% 45%, 93% 60%, 98% 75%, 91% 90%, 100% 100%, 0% 100%);
    }

    .wing-art {
        flex: 1;
        background-color: #ede0c8;
        padding: 45px;
        color: #2c1a1a;
        margin-left: -35px;
        clip-path: polygon(6% 0%, 100% 0%, 100% 100%, 8% 100%, 2% 85%, 10% 70%, 1% 55%, 9% 40%, 3% 25%, 11% 10%);
    }

    .map-header { font-family: 'Lobster', cursive; font-size: 2.6rem; margin-bottom: 20px; }
    .map-text { font-family: 'Shadows Into Light', cursive; font-size: 1.6rem; line-height: 1.4; }

    /* MOBILE GUARD */
    @media (max-width: 800px) {
        .tear-wrapper { flex-direction: column; }
        .wing-science, .wing-art { clip-path: none !important; margin: 15px 0; border-radius: 25px; }
    }
    </style>
    
    <div class="sky-header">
        <h1 class="sparkle-title">Stargaze</h1>
        <p style="font-family: 'Inter', sans-serif; letter-spacing: 2px; font-weight: bold;">WHERE ART MEETS THE INFINITE</p>
    </div>
""", unsafe_allow_html=True)

# 3.3: ACCESS GATE LOGIC
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    # --- LOGIN & SIGNUP VIEWS ---
    login_tab, signup_tab = st.tabs(["🔒 Welcome Back", "🚀 Begin Journey"])
    with login_tab:
        with st.form("log"):
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Enter the Observatory"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and check_pass(p, res.data[0]['password_hash']):
                    st.session_state.logged_in = True
                    st.session_state.user = res.data[0]
                    st.rerun()
                else: st.error("Credentials not recognized.")
    with signup_tab:
        with st.form("reg"):
            email_reg = st.text_input("Email")
            name_reg = st.text_input("Preferred Name")
            pw_reg = st.text_input("Password", type="password")
            if st.form_submit_button("Join Us"):
                if is_valid_email(email_reg) and len(pw_reg) >= 6:
                    hashed = hash_pass(pw_reg)
                    supabase.table("users").insert({"username": email_reg, "name": name_reg, "password_hash": hashed}).execute()
                    st.success("Welcome aboard! Please Log In.")
                else: st.error("Use a valid email and 6+ character password.")

# 3.5: THE MAIN PORTAL (Logged-In)
else:
    if "has_seen_intro" not in st.session_state:
        welcome_popup()

    st.sidebar.markdown(f"## {st.session_state.user['name']} ✨")
    if st.sidebar.button("✨ Leave Observatory"):
        st.session_state.logged_in = False
        st.rerun()
    
    # THE TRUE MODERN SELECT SLIDER
    mode_select = st.select_slider(
        "Lens Selection",
        options=["Science Hub", "The Observatory", "Creative Gallery"],
        value="The Observatory",
        label_visibility="collapsed"
    )

    if mode_select == "The Observatory":
        st.markdown("""
            <div class="tear-wrapper">
                <div class="wing-science">
                    <h2 class="map-header" style="color: #003366;">📜 The Blueprint</h2>
                    <div class="map-text">
                        <b>MODE: OBJECTIVE DATA</b><br><br>
                        Strip away the color. Find the math.<br>
                        Verify the Geometric Fingerprint.<br><br>
                        <i>Verify your capture to begin analysis.</i>
                    </div>
                </div>
                <div class="wing-art">
                    <h2 class="map-header" style="color: #660000;">🕯️ The Canvas</h2>
                    <div class="map-text">
                        <b>MODE: SUBJECTIVE WONDER</b><br><br>
                        The stars are more than pixels.<br>
                        Capture the story. Build your soul's catalog.<br><br>
                        <i>The stars are waiting for your essence.</i>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    elif mode_select == "Science Hub":
        st.title("🔬 Science Terminal")
        # INSERT: EXIF Checker & detection here
        
    elif mode_select == "Creative Gallery":
        st.title("🎨 Celestial Gallery")
        # INSERT: Aesthetic filters & story-telling here
