import streamlit as st
import cv2
import numpy as np
import json
import bcrypt
import re
import base64

def get_base64_image(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()
DASHBOARD_BG = get_base64_image("dashboard_bg.png")
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
# 3.2: THE CSS VAULT (Clean & Conditional)

def inject_css():
    if st.session_state.get("logged_in", False):
        bg = f"""
        background:
            linear-gradient(180deg, rgba(10, 10, 25, 0.85) 0%, rgba(0, 0, 0, 0.95) 100%),
            url("data:image/png;base64,{DASHBOARD_BG}");
        """
        subtitle = "THE OBSERVATORY"
    else:
        bg = """
        background:
            linear-gradient(180deg, rgba(50, 50, 50, 0.7) 0%, rgba(0, 0, 0, 0.9) 100%),
            url("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1280px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg");
        """
        subtitle = "WHERE ART MEETS THE INFINITE"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lobster&family=Inter:wght@400;700&display=swap');

    .stApp {{
        {bg}
        background-attachment: fixed;
        background-size: cover;
        background-position: center;
    }}

    .stApp::before {{
        content: "";
    position: fixed;
    inset: 0;
    background: radial-gradient(circle at center,
        rgba(0,0,0,0.55) 0%,
        rgba(0,0,0,0.25) 40%,
        rgba(255,255,255,0.12) 100%);
    z-index: -1;
    }}

    .sky-header {{
        background: linear-gradient(180deg, #000000 0%, #060b26 70%, #0c1445 100%);
        padding: 40px 10px;
        text-align: center;
        border-bottom: 3px solid #4A90E2;
        border-radius: 0 0 40px 40px;
        margin-bottom: 30px;
    }}

    .sparkle-title {{
        font-family: 'Lobster', cursive !important;
        font-size: clamp(2.5rem, 8vw, 5rem) !important;
        color: white !important;
        text-shadow: 0 0 10px #fff, 0 0 20px #4A90E2;
        animation: title-glow 2s ease-in-out infinite alternate;
        white-space: nowrap;
    }}

    @keyframes title-glow {{
        from {{ text-shadow: 0 0 10px #fff; }}
        to {{ text-shadow: 0 0 20px #fff, 0 0 30px #4A90E2; }}
    }}
    [data-testid="stForm"] {{
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(15px);
        border-radius: 30px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 30px !important;
        max-width: 450px;
        margin: auto;
    }}

    label, p, .stButton, .stTextInput, .stSelectSlider {{
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
    }}
    </style>

    <div class="sky-header">
        <h1 class="sparkle-title">Stargaze</h1>
        <p style="font-family: 'Inter', sans-serif; letter-spacing: 2px; font-size: 0.9rem;">
            {subtitle}
        </p>
    </div>
    """, unsafe_allow_html=True)

inject_css()

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
    # 3.5: MAIN OBSERVATORY (Logged-In State)
else:
    if "has_seen_intro" not in st.session_state:
        welcome_popup()

    st.sidebar.markdown(f"## {st.session_state.user['name']} ✨")
    if st.sidebar.button("✨ Leave Observatory"):
        st.session_state.logged_in = False
        st.rerun()
    
    # THE MODERN ORB SLIDER
    mode = st.select_slider(
        "Calibration", 
        options=["Science", "Neutral", "Gallery"], 
        value="Neutral", 
        label_visibility="collapsed"
    )

    # 3.5.1: NEUTRAL MODE (The Split Vision)
    if mode == "Neutral":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
                <div class="glass-pane">
                    <h2 style="font-family:Lobster; color:#4A90E2;">The Blueprint</h2>
                    <p><b>Objective Extraction.</b><br><br>
                    Strip away the color. Find the math. Verify the coordinates and 
                    geometric fingerprints of the stars. 
                    Pure mathematical identification.</p>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
                <div class="glass-pane">
                    <h2 style="font-family:Lobster; color:#E0E1DD;">The Canvas</h2>
                    <p><b>Subjective Wonder.</b><br><br>
                    The stars are more than pixels. Extract the emotional essence 
                    of your capture, add artistic overlays, and archive your 
                    celestial memories.</p>
                </div>
            """, unsafe_allow_html=True)

    # 3.5.2: SCIENCE MODE (The Functional Engine)
    elif mode == "Science":
        st.markdown("<h2 style='font-family:Lobster;'>🔬 Science Terminal</h2>", unsafe_allow_html=True)
        
        # The restored File Uploader
        uploaded = st.file_uploader("Upload Star Capture", type=['jpg', 'jpeg', 'png'])
        
        if uploaded:
            # 1. Security Check (EXIF)
            valid, msg = authenticate_image(uploaded)
            if not valid:
                st.error(msg)
            else:
                st.success(msg)
                
                # 2. Backbone Processing
                with st.spinner("Decoding celestial coordinates..."):
                    # We use .getvalue() to read the bytes for OpenCV
                    stars, img = stargaze_engine(uploaded.getvalue(), 120, 4)
                    winner, geom, status = match_patterns(stars)
                    
                    # 3. Display Results
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Stars Detected", len(stars))
                        if winner: 
                            st.success(f"Pattern Identified: **{winner}**")
                        else: 
                            st.warning(f"Status: {status}")
                    
                    with col_b:
                        # Convert BGR to RGB for Streamlit display
                        st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption="Processed Analysis", use_container_width=True)

    # 3.5.3: GALLERY MODE (Placeholder)
    else:
        st.markdown("<h2 style='font-family:Lobster;'>🎨 Celestial Gallery</h2>", unsafe_allow_html=True)
        st.info("Your personal constellation catalog is coming soon...")
# 3.5.1: THE ANCIENT TORN PORTAL (SVG Rendered)

# This block creates the physical "Tear" using coordinate-based SVG paths.
