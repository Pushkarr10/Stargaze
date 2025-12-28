import streamlit as st
import cv2
import numpy as np
import json
import bcrypt
import re
import base64
from scipy.spatial import Delaunay
from supabase import create_client, Client

# =================================================================
# 🧬 ZONE 1: THE BACKBONE (Geometric Engine & Validators)
# =================================================================

def get_base64_image(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return "" 

DASHBOARD_BG = get_base64_image("dashboard_bg.png")

def authenticate_image(uploaded_file):
    if uploaded_file is None:
        return False, "No signal detected."
    if uploaded_file.size > 10 * 1024 * 1024:
        return False, "Signal too strong (File > 10MB). Please compress."
    return True, "Signal locked. Telemetry received."

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
    except: return None, None, "Star Database Offline."
    
    if len(stars) < 4: return None, None, "Insufficient data points (Need 4+ stars)."
    
    tri = Delaunay(stars)
    matches = {}
    valid_simplices = []
    for simplex in tri.simplices:
        p1, p2, p3 = stars[simplex]
        side_lens = sorted([np.linalg.norm(p1-p2), np.linalg.norm(p2-p3), np.linalg.norm(p3-p1)])
        if side_lens[2] == 0: continue
        
        barcode = [round(side_lens[0]/side_lens[2], 2), round(side_lens[1]/side_lens[2], 2)]
        for name, fingerprints in db.items():
            for fp in fingerprints:
                if all(abs(b - f) < 0.05 for b, f in zip(barcode, fp)):
                    matches[name] = matches.get(name, 0) + 1
                    valid_simplices.append(simplex)
    
    if not matches: return None, None, "Unknown Constellation."
    return max(matches, key=matches.get), valid_simplices, "Pattern Identified."

# =================================================================
# 🧠 ZONE 2: THE BRAIN (Database & Security - FIXED)
# =================================================================

# We use @st.cache_resource to keep the connection alive
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        return None

supabase = init_supabase()

# If connection failed completely
if supabase is None:
    st.error("🚨 Critical System Failure: Unable to connect to Supabase. Check your .streamlit/secrets.toml file.")
    st.stop()

def hash_pass(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def check_pass(p, h): return bcrypt.checkpw(p.encode(), h.encode())
def is_valid_email(email): return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

# =================================================================
# 🎨 ZONE 3: THE INTERFACE (The Celestial Sanctuary)
# =================================================================

# 3.1: THE DIALOG (Onboarding)
@st.dialog("Welcome to the Observatory! 🔭")
def welcome_popup():
    st.markdown("""
    ### System Online 🌌
    
    **Calibrate your experience:**
    
    * 👈 **Slide Left:** For scientific analysis and pattern recognition.
    * 👉 **Slide Right:** For visual archiving and artistic curation.
    """)
    if st.button("Initialize"):
        st.session_state.has_seen_intro = True
        st.rerun()

# 3.2: THE CSS VAULT
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

    .sky-header {{
        background: linear-gradient(180deg, #000000 0%, #060b26 70%, #0c1445 100%);
        padding: 40px 10px;
        text-align: center;
        border-bottom: 1px solid rgba(74, 144, 226, 0.3);
        border-radius: 0 0 40px 40px;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}

    .sparkle-title {{
        font-family: 'Lobster', cursive !important;
        font-size: clamp(2.5rem, 8vw, 5rem) !important;
        color: white !important;
        text-shadow: 0 0 10px #fff, 0 0 20px #4A90E2;
        animation: title-glow 3s ease-in-out infinite alternate;
    }}

    @keyframes title-glow {{
        from {{ text-shadow: 0 0 10px #fff; opacity: 0.9; }}
        to {{ text-shadow: 0 0 25px #fff, 0 0 40px #4A90E2; opacity: 1; }}
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

    .glass-pane {{
        background: rgba(20, 20, 35, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        height: 100%;
        transition: all 0.3s ease;
    }}
    
    .glass-pane:hover {{
        transform: translateY(-5px);
        border: 1px solid rgba(74, 144, 226, 0.5);
        box-shadow: 0 0 20px rgba(74, 144, 226, 0.2);
    }}

    h3 {{ font-family: 'Inter', sans-serif !important; font-weight: 700; }}
    label, p, .stButton, .stTextInput, .stSelectSlider {{
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
    }}
    </style>

    <div class="sky-header">
        <h1 class="sparkle-title">Stargaze</h1>
        <p style="font-family: 'Inter', sans-serif; letter-spacing: 4px; font-size: 0.8rem; text-transform: uppercase; opacity: 0.8;">
            {subtitle}
        </p>
    </div>
    """, unsafe_allow_html=True)

inject_css()

# 3.3: SESSION & PERSISTENCE
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "show_signup" not in st.session_state: st.session_state.show_signup = False

# 3.4: THE ACCESS GATE
if not st.session_state.logged_in:
    
    if st.session_state.show_signup:
        with st.form("reg"):
            st.write("### ✨ Join the Observatory")
            email = st.text_input("Email Address")
            name = st.text_input("Callsign (Username)")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Initiate Launch Sequence"):
                if is_valid_email(email) and len(pw) >= 6:
                    hashed = hash_pass(pw)
                    try:
                        supabase.table("users").insert({"username": email, "name": name, "password_hash": hashed}).execute()
                        st.success("Registration complete. Please log in.")
                        st.session_state.show_signup = False
                        st.rerun()
                    except Exception as e:
                        st.error("This frequency (email) is already taken.")
                else: st.error("Invalid credentials. Password must be 6+ chars.")
        
        if st.button("Return to Login"):
            st.session_state.show_signup = False
            st.rerun()

    else:
        with st.form("log"):
            st.write("### ✨ Welcome Back")
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Open the Skies"):
                try:
                    # Using the cached 'supabase' object
                    res = supabase.table("users").select("*").eq("username", u).execute()
                    if res.data and check_pass(p, res.data[0]['password_hash']):
                        st.session_state.logged_in = True
                        st.session_state.user = res.data[0]
                        st.rerun()
                    else: st.error("Access Denied: Incorrect Coordinates.")
                except Exception as e:
                    st.error(f"Network error: {str(e)}")
        
        if st.button("New Recruit? Sign Up"):
            st.session_state.show_signup = True
            st.rerun()

# 3.5: MAIN OBSERVATORY
else:
    if "has_seen_intro" not in st.session_state:
        welcome_popup()

    st.sidebar.markdown(f"## {st.session_state.user['name']} 🔭")
    if st.sidebar.button("✨ Leave Observatory", key="logout_btn_main"):
        st.session_state.logged_in = False
        st.session_state.has_seen_intro = False
        st.rerun()
    
    mode = st.select_slider(
        "Calibration", 
        options=["Science", "Neutral", "Gallery"], 
        value="Neutral", 
        label_visibility="collapsed"
    )

    if mode == "Neutral":
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
                <div class="glass-pane">
                    <h3 style="color:#4A90E2; font-size: 1.5rem;">📐 Deep Space Analysis</h3>
                    <p style="opacity: 0.8; font-size: 0.9rem; margin-top: 15px;">
                        Isolate the geometry of the stars. Strip away the noise to reveal 
                        the mathematical fingerprints of the constellations.
                    </p>
                    <p style="color: #4A90E2; font-weight: bold; margin-top: 20px;">
                        &larr; Slide Left to Analyze
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
                <div class="glass-pane">
                    <h3 style="color:#E0E1DD; font-size: 1.5rem;">📼 The Cosmic Archive</h3>
                    <p style="opacity: 0.8; font-size: 0.9rem; margin-top: 15px;">
                        Curate your personal collection of the heavens. Apply artistic filters
                        and save your discoveries to your permanent log.
                    </p>
                    <p style="color: #E0E1DD; font-weight: bold; margin-top: 20px;">
                        Slide Right to Curate &rarr;
                    </p>
                </div>
            """, unsafe_allow_html=True)

    elif mode == "Science":
        st.markdown("<h2 style='font-family:Lobster; text-align:center;'>🔬 Science Terminal</h2>", unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload Star Capture", type=['jpg', 'jpeg', 'png'])
        
        if uploaded:
            valid, msg = authenticate_image(uploaded) 
            if not valid:
                st.error(msg)
            else:
                st.success(msg)
                with st.spinner("Decoding celestial coordinates..."):
                    stars, img = stargaze_engine(uploaded.getvalue(), 120, 4)
                    winner, geom, status = match_patterns(stars)
                    
                    col_res1, col_res2 = st.columns([1, 2])
                    with col_res1:
                        st.write(f"**Stars Detected:** `{len(stars)}`")
                        if winner: 
                            st.success(f"**Target:** {winner}")
                        else: 
                            st.warning(status)
                    with col_res2:
                        st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption="Processed Telemetry", use_column_width=True)

    else:
        st.markdown("<h2 style='font-family:Lobster; text-align:center;'>🎨 The Archive</h2>", unsafe_allow_html=True)
        st.info("Accessing long-term storage... (Feature arriving in next update)")
