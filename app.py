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
# 🎨 ZONE 3: THE INTERFACE (Artistic & Validated UX)
# =================================================================

# 1. PAGE SETUP & ARTISTIC CSS
st.set_page_config(page_title="Stargaze AI", page_icon="🌌", layout="wide")

# This block "paints" your app with the Starry Night theme and custom fonts
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lobster&family=Caveat&family=Shadows+Into+Light&display=swap');

    /* The Main Background - Starry Night */
    .stApp {
        background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1280px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg");
        background-attachment: fixed;
        background-size: cover;
    }

    /* Night Sky Header with Shooting Star Animation */
    .sky-header {
        background: linear-gradient(to bottom, #000000 0%, #0c1445 100%);
        padding: 40px;
        text-align: center;
        border-bottom: 2px solid #4A90E2;
        border-radius: 0 0 50px 50px;
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
    }

    .shooting-star {
        position: absolute;
        top: 0; left: 80%;
        width: 4px; height: 4px;
        background: white;
        opacity: 0;
        box-shadow: 0 0 10px 2px white;
        animation: shoot 4s linear infinite;
    }

    @keyframes shoot {
        0% { transform: translateX(0) translateY(0); opacity: 1; }
        20% { transform: translateX(-400px) translateY(400px); opacity: 0; }
        100% { opacity: 0; }
    }

    /* Applying fonts to specific elements */
    h1, h2, h3 {
        font-family: 'Lobster', cursive !important;
        color: #f0f0f0 !important;
        text-shadow: 3px 3px 6px #000;
    }
    
    .stMarkdown, p, label, .stTabs {
        font-family: 'Caveat', cursive !important;
        font-size: 1.6rem !important;
        color: #ffffff !important;
    }

    /* Glassmorphism for Forms */
    [data-testid="stForm"] {
        background: rgba(0, 0, 0, 0.6) !important;
        backdrop-filter: blur(15px);
        border-radius: 25px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        padding: 30px !important;
    }
    </style>
    
    <div class="sky-header">
        <div class="shooting-star"></div>
        <h1>Stargaze AI</h1>
        <p>A Digital Sanctuary for the Celestial Curious</p>
    </div>
    """, unsafe_allow_html=True)

# 2. SESSION & ONBOARDING LOGIC
if "logged_in" not in st.session_state: st.session_state.logged_in = False

# --- LOGOUT FIX: THE FIRST THING WE CHECK ---
if st.session_state.logged_in:
    if st.sidebar.button("✨ Leave the Observatory"):
        st.session_state.logged_in = False
        st.session_state.has_seen_intro = False # Reset intro for next time
        st.rerun()

# 3. ACCESS GATE (Login / Signup)
if not st.session_state.logged_in:
    login_tab, signup_tab = st.tabs(["🔒 Resume Exploration", "🚀 Begin Journey"])

    with signup_tab:
        with st.form("reg"):
            st.markdown("### Create Your Profile")
            email = st.text_input("Email")
            name = st.text_input("Name")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Initialize Account"):
                if is_valid_email(email) and len(pw) >= 6:
                    hashed = hash_pass(pw)
                    supabase.table("users").insert({"username": email, "name": name, "password_hash": hashed}).execute()
                    st.success("Your profile is written in the stars. Please Log In.")
                else: st.error("Please provide valid credentials (Min 6 chars for password).")

    with login_tab:
        with st.form("log"):
            st.markdown("### Enter the Observatory")
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Authenticate"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and check_pass(p, res.data[0]['password_hash']):
                    st.session_state.logged_in = True
                    st.session_state.user = res.data[0]
                    st.rerun() # FORCE REFRESH TO HIDE LOGIN
                else: st.error("Invalid Credentials.")

# 4. THE OBSERVATORY DASHBOARD
else:
    if "has_seen_intro" not in st.session_state:
        welcome_popup()

    st.sidebar.markdown(f"## Welcome, {st.session_state.user['name']} ✨")
    
    # --- MODULE A: DUAL-ZONE SWITCHER ---
    mode = st.select_slider(
        "Adjust Your Lens",
        options=["Science Hub", "The Observatory", "Creative Gallery"],
        value="The Observatory"
    )

    if mode == "Science Hub":
        st.markdown("<style>.main { background: #0b0d12 !important; font-family: 'Courier New' !important; }</style>", unsafe_allow_html=True)
        st.title("🔬 TECHNICAL ANALYSIS")
        # Technical content goes here
        
    elif mode == "Creative Gallery":
        st.markdown("<style>.main { background: #1a1a2e !important; font-family: 'Georgia' !important; }</style>", unsafe_allow_html=True)
        st.title("🎨 CELESTIAL GALLERY")
        # Artistic content goes here

    else: # The Observatory (Standard Mode)
        st.title("🌌 Main Observatory Feed")
        uploaded = st.file_uploader("Upload Star Photo", type=['jpg', 'jpeg', 'png'])

        if uploaded:
            # --- MODULE B: AUTHENTICATION & PROCESSING ---
            stars, img = stargaze_engine(uploaded.read(), 120, 4)
            winner, geom, status = match_patterns(stars)
            
            col1, col2 = st.columns(2)
            with col1:
                st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption="Raw Capture")
            with col2:
                if winner: 
                    st.success(f"Pattern Verified: {winner}")
                    # Drawing logic would go here
                else: 
                    st.info(status)
