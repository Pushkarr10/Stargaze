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

# 3.2: THE CSS VAULT (The Visual Identity)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lobster&family=Inter:wght@400;700&display=swap');

    /* The Main Background with Gradient Overlay */
    .stApp {
        background: 
            linear-gradient(180deg, rgba(50, 50, 50, 0.7) 0%, rgba(0, 0, 0, 0.9) 100%),
            url("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1280px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg");
        background-attachment: fixed;
        background-size: cover;
    }

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
        to { text-shadow: 0 0 20px #fff, 0 0 30px #4A90E2; }
    }

    .shooting-star {
        position: absolute;
        top: 0; left: 80%;
        width: 3px; height: 3px;
        background: white;
        animation: shoot 5s linear infinite;
    }
    
    @keyframes shoot {
        0% { transform: translateX(0) translateY(0); opacity: 1; }
        15% { transform: translateX(-300px) translateY(300px); opacity: 0; }
        100% { opacity: 0; }
    }

    /* Form and Text Styling */
    [data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(15px);
        border-radius: 30px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 30px !important;
        max-width: 450px;
        margin: auto;
    }

    label, p, .stButton, .stTextInput, .stSelectSlider {
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
    }
    </style>
    
    <div class="sky-header">
        <div class="shooting-star"></div>
        <h1 class="sparkle-title">Stargaze</h1>
        <p style="font-family: 'Inter', sans-serif; letter-spacing: 2px; font-size: 0.9rem;">WHERE ART MEETS THE INFINITE</p>
    </div>
    """, unsafe_allow_html=True)
# 3.3: SESSION & PERSISTENCE LOGIC
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "show_signup" not in st.session_state: st.session_state.show_signup = False

if st.session_state.logged_in:
    if st.sidebar.button("✨ Leave Observatory"):
        st.session_state.logged_in = False
        st.session_state.has_seen_intro = False
        st.rerun()

# 3.4: THE ACCESS GATE (Login / Signup Switch)
if not st.session_state.logged_in:
    
    if st.session_state.show_signup:
        # --- 3.4.1: SIGN UP FORM ---
        with st.form("reg"):
            st.write("### ✨ Join the Observatory")
            email = st.text_input("Email Address")
            name = st.text_input("What should we call you?")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Create Account"):
                if is_valid_email(email) and len(pw) >= 6:
                    hashed = hash_pass(pw)
                    supabase.table("users").insert({"username": email, "name": name, "password_hash": hashed}).execute()
                    st.success("Welcome! You can now log in.")
                else: st.error("Please use a valid email and 6+ character password.")
        
        if st.button("Back to Login"):
            st.session_state.show_signup = False
            st.rerun()

    else:
        # --- 3.4.2: LOGIN FORM ---
        with st.form("log"):
            st.write("### ✨ Welcome Back")
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Open the Skies"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and check_pass(p, res.data[0]['password_hash']):
                    st.session_state.logged_in = True
                    st.session_state.user = res.data[0]
                    st.rerun()
                else: st.error("Credentials not recognized.")
        
        if st.button("New here? Create an Account"):
            st.session_state.show_signup = True
            st.rerun()

# 3.5: THE MAIN OBSERVATORY (Logged-In State)
else:
    if "has_seen_intro" not in st.session_state:
        welcome_popup()

    st.sidebar.markdown(f"## {st.session_state.user['name']} ✨")
# 3.5.1: THE ANCIENT TORN PORTAL (SVG Rendered)

# This block creates the physical "Tear" using coordinate-based SVG paths.
st.markdown("""
    <style>
    /* 1. THE VPN-STYLE SWITCH (Thick, Smooth, Modern) */
    .stRadio > div {
        background: #1a1a1a !important;
        border: 4px solid #4A90E2 !important;
        border-radius: 60px !important;
        padding: 8px 20px !important;
        max-width: 400px;
        margin: 0 auto 40px auto;
        box-shadow: 0 0 20px rgba(74, 144, 226, 0.3);
    }
    
    /* 2. THE TORN MAP CONTAINER */
    .tear-wrapper {
        display: flex;
        width: 100%;
        min-height: 500px;
        position: relative;
        overflow: visible;
        filter: drop-shadow(0px 15px 30px rgba(0,0,0,0.7));
    }

    /* THE SCIENCE WING (LEFT) */
    .wing-science {
        flex: 1;
        background-color: #f4e4bc; /* Aged Parchment */
        background-image: radial-gradient(rgba(0,0,0,0.1) 1px, transparent 1px);
        background-size: 25px 25px; /* Subtle graph/blueprint pattern */
        padding: 45px;
        color: #1a1a1a;
        /* THE JAGGED CLIP-PATH */
        clip-path: polygon(0% 0%, 96% 0%, 100% 15%, 92% 30%, 100% 45%, 93% 60%, 98% 75%, 91% 90%, 100% 100%, 0% 100%);
        border-right: 1px solid rgba(0,0,0,0.1);
        z-index: 2;
    }

    /* THE ART WING (RIGHT) */
    .wing-art {
        flex: 1;
        background-color: #ede0c8; /* Slightly darker vellum */
        padding: 45px;
        color: #2c1a1a;
        margin-left: -35px; /* Overlap creates the 'rip' depth */
        /* ASYMMETRIC MATCHING TEAR */
        clip-path: polygon(6% 0%, 100% 0%, 100% 100%, 8% 100%, 2% 85%, 10% 70%, 1% 55%, 9% 40%, 3% 25%, 11% 10%);
        z-index: 1;
    }

    /* TYPOGRAPHY FOR THE MAP */
    .map-header {
        font-family: 'Lobster', cursive;
        font-size: 2.5rem;
        margin-bottom: 20px;
        border-bottom: 2px solid rgba(0,0,0,0.1);
    }

    .map-text {
        font-family: 'Shadows Into Light', cursive;
        font-size: 1.5rem;
        line-height: 1.4;
    }

    /* MOBILE RESPONSIVENESS: Stacks wings so they don't distort */
    @media (max-width: 800px) {
        .tear-wrapper { flex-direction: column; }
        .wing-science, .wing-art { clip-path: none !important; margin: 10px 0; border-radius: 20px; }
    }
    </style>
""", unsafe_allow_html=True)

# 3.5.2: THE PORTAL LOGIC
mode_select = st.radio(
    "Choose Your Lens",
    ["Science Hub", "The Observatory", "Creative Gallery"],
    index=1,
    horizontal=True,
    label_visibility="collapsed"
)

if mode_select == "The Observatory":
    st.markdown("""
        <div class="tear-wrapper">
            <div class="wing-science">
                <h2 class="map-header" style="color: #003366;">📜 The Blueprint</h2>
                <div class="map-text">
                    <b>MODE: OBJECTIVE DATA</b><br><br>
                    Coordinates: [Scanning...]<br>
                    Geometric Fingerprints: [Pending]<br><br>
                    <i>Strip away the color. Find the math. Verify the stars.</i>
                </div>
            </div>
            <div class="wing-art">
                <h2 class="map-header" style="color: #660000;">🕯️ The Canvas</h2>
                <div class="map-text">
                    <b>MODE: SUBJECTIVE WONDER</b><br><br>
                    Memories: [0 Found]<br>
                    Emotional Essence: [Active]<br><br>
                    <i>The stars are not just pixels. Capture the story. Build your soul's catalog.</i>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

elif mode_select == "Science Hub":
    st.title("🔬 Science Terminal")
    # Technical logic...

elif mode_select == "Creative Gallery":
    st.title("🎨 Celestial Gallery")
    # Artistic logic...
