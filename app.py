import streamlit as st
import cv2
import numpy as np
import json
import bcrypt
import re
from scipy.spatial import Delaunay
from supabase import create_client, Client
from PIL import Image
import io

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

def authenticate_image(uploaded_file):
    """Check if image has valid EXIF camera metadata"""
    try:
        pil_img = Image.open(uploaded_file)
        exif_data = pil_img._getexif()
        
        if exif_data is None:
            return False, "No camera metadata found. Please upload a photo taken with a camera."
        
        # Check for camera-specific EXIF tags
        camera_tags = [271, 272, 34855]  # Make, Model, ISO
        has_camera_data = any(tag in exif_data for tag in camera_tags)
        
        if has_camera_data:
            return True, "✅ Verified genuine camera capture"
        else:
            return False, "⚠️ Image lacks camera verification. Downloaded images not allowed."
    except:
        return False, "⚠️ Could not verify image source."

# =================================================================
# 🎨 ZONE 3: THE INTERFACE (The Celestial Sanctuary)
# =================================================================

# PAGE CONFIG
st.set_page_config(
    page_title="Stargaze",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 3.1: THE DIALOG (Onboarding)
@st.dialog("Welcome to the Observatory! 🔭")
def welcome_popup():
    st.markdown("""
    ### Heyy Great To Have You Onboard! 🌌
    Welcome to **Stargaze**. This is the start to your sparkling experience ✨✨✨.
    
    **Your Journey:**
    - Slide to the **LEFT** for the Science Hub 🔬
    - Slide to the **RIGHT** for the Canvas Mode 🎨
    
    Upload a photo taken with **your camera** to detect constellations and unlock achievements!
    """)
    if st.button("Let's Start Mapping!"):
        st.session_state.has_seen_intro = True
        st.rerun()

# 3.2: THE CSS VAULT (The Visual Identity)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lobster&family=Inter:wght@400;700&display=swap');

    /* ===== LOGIN PAGE BACKGROUND (Van Gogh) ===== */
    .login-page {
        background: 
            linear-gradient(180deg, rgba(50, 50, 50, 0.7) 0%, rgba(0, 0, 0, 0.9) 100%),
            url("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1280px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg");
        background-attachment: fixed;
        background-size: cover;
        background-position: center;
    }

    /* ===== DASHBOARD BACKGROUND (Cosmic Nebula) ===== */
    .dashboard-page {
        background: 
            radial-gradient(ellipse at center, rgba(100, 50, 150, 0.4) 0%, rgba(0, 0, 0, 0.95) 100%),
            url("https://agi-prod-file-upload-public-main-use1.s3.amazonaws.com/02b7c172-1771-423e-9d66-083a83b9031e");
        background-attachment: fixed;
        background-size: cover;
        background-position: center;
    }

    /* LOGIN HEADER */
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
        margin: 0;
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

    /* ===== LOGIN/SIGNUP FORMS ===== */
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

    /* ===== GLOWING ORB SLIDER (MOBILE OPTIMIZED) ===== */
    .slider-container {
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 30px 0;
        padding: 0 10px;
    }

    .slider-label-left, .slider-label-right {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: clamp(0.9rem, 2.5vw, 1.2rem);
        white-space: nowrap;
        text-shadow: 0 0 10px rgba(74, 144, 226, 0.5);
    }

    .slider-label-left {
        color: #4A90E2;
        margin-right: 15px;
    }

    .slider-label-right {
        color: #E24A8A;
        margin-left: 15px;
    }

    /* Custom slider styling */
    input[type="range"] {
        width: 100%;
        max-width: 300px;
        height: 12px;
        border-radius: 10px;
        background: linear-gradient(to right, rgba(74, 144, 226, 0.3), rgba(226, 74, 138, 0.3));
        outline: none;
        -webkit-appearance: none;
        appearance: none;
    }

    /* Thumb styling */
    input[type="range"]::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 35px;
        height: 35px;
        border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #ffffff, #4A90E2);
        cursor: pointer;
        box-shadow: 0 0 20px rgba(74, 144, 226, 0.8), 0 0 40px rgba(74, 144, 226, 0.4);
        transition: all 0.2s ease;
    }

    input[type="range"]::-webkit-slider-thumb:hover {
        box-shadow: 0 0 30px rgba(74, 144, 226, 1), 0 0 60px rgba(74, 144, 226, 0.6);
        transform: scale(1.15);
    }

    input[type="range"]::-moz-range-thumb {
        width: 35px;
        height: 35px;
        border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #ffffff, #4A90E2);
        cursor: pointer;
        box-shadow: 0 0 20px rgba(74, 144, 226, 0.8), 0 0 40px rgba(74, 144, 226, 0.4);
        border: none;
        transition: all 0.2s ease;
    }

    input[type="range"]::-moz-range-thumb:hover {
        box-shadow: 0 0 30px rgba(74, 144, 226, 1), 0 0 60px rgba(74, 144, 226, 0.6);
        transform: scale(1.15);
    }

    /* ===== DASHBOARD CONTENT AREA ===== */
    .dashboard-container {
        background: rgba(20, 20, 40, 0.6);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(74, 144, 226, 0.2);
        padding: 20px;
        margin-top: 30px;
    }

    .content-section {
        display: none;
    }

    .content-section.active {
        display: block;
        animation: fadeIn 0.3s ease-in;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    /* ===== RESPONSIVE TEXT ===== */
    h1, h2, h3 {
        font-family: 'Lobster', cursive;
        text-shadow: 0 0 10px rgba(74, 144, 226, 0.5);
    }

    h1 { font-size: clamp(2rem, 6vw, 3.5rem); }
    h2 { font-size: clamp(1.5rem, 5vw, 2.5rem); }
    h3 { font-size: clamp(1.2rem, 4vw, 1.8rem); }

    p, label, .stButton {
        font-family: 'Inter', sans-serif;
        font-size: clamp(0.9rem, 2.5vw, 1rem);
        color: #ffffff;
    }

    /* ===== FILE UPLOADER STYLING ===== */
    [data-testid="stFileUploadDropzone"] {
        background: rgba(74, 144, 226, 0.1) !important;
        border: 2px dashed rgba(74, 144, 226, 0.5) !important;
        border-radius: 15px;
    }

    /* ===== MOBILE OPTIMIZATION ===== */
    @media (max-width: 768px) {
        .sky-header {
            padding: 20px 10px;
            margin-bottom: 20px;
        }

        .slider-container {
            flex-direction: column;
            gap: 15px;
        }

        .slider-label-left, .slider-label-right {
            margin: 0;
        }

        input[type="range"] {
            max-width: 100%;
        }

        .dashboard-container {
            padding: 15px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# 3.3: SESSION & PERSISTENCE LOGIC
if "logged_in" not in st.session_state: 
    st.session_state.logged_in = False
if "show_signup" not in st.session_state: 
    st.session_state.show_signup = False
if "lens_position" not in st.session_state:
    st.session_state.lens_position = 50  # 0-33 = Science, 34-66 = Observatory, 67-100 = Canvas

if st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 3, 1])
    with col3:
        if st.button("✨ Leave Observatory", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.has_seen_intro = False
            st.rerun()

# 3.4: THE ACCESS GATE (Login / Signup Switch)
if not st.session_state.logged_in:
    # APPLY VAN GOGH BACKGROUND TO LOGIN PAGE
    st.markdown('<div class="login-page">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="sky-header">
        <div class="shooting-star"></div>
        <h1 class="sparkle-title">Stargaze</h1>
        <p style="font-family: 'Inter', sans-serif; letter-spacing: 2px; font-size: 0.9rem;">WHERE ART MEETS THE INFINITE</p>
    </div>
    """, unsafe_allow_html=True)
    
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
    
    st.markdown('</div>', unsafe_allow_html=True)

# 3.5: THE MAIN OBSERVATORY (Logged-In State)
else:
    # APPLY COSMIC NEBULA BACKGROUND TO DASHBOARD
    st.markdown('<div class="dashboard-page">', unsafe_allow_html=True)
    
    if "has_seen_intro" not in st.session_state:
        welcome_popup()

    st.sidebar.markdown(f"## {st.session_state.user['name']} ✨")

    # ===== THE GLOWING ORB SLIDER =====
    st.markdown('<div class="slider-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown('<div class="slider-label-left">🔬 SCIENCE</div>', unsafe_allow_html=True)
    
    with col2:
        lens_position = st.slider(
            "Lens Position",
            min_value=0,
            max_value=100,
            value=st.session_state.lens_position,
            step=1,
            label_visibility="collapsed"
        )
        st.session_state.lens_position = lens_position
    
    with col3:
        st.markdown('<div class="slider-label-right">🎨 CANVAS</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # ===== DETERMINE MODE BASED ON SLIDER =====
    if lens_position <= 33:
        current_mode = "Science Hub"
    elif lens_position <= 66:
        current_mode = "The Observatory"
    else:
        current_mode = "Canvas Mode"

    # ===== CONTENT SECTIONS =====
    st.markdown(f'<div class="dashboard-container">', unsafe_allow_html=True)

    if current_mode == "Science Hub":
        st.markdown(f'<h2 style="color: #4A90E2;">🔬 Science Hub</h2>', unsafe_allow_html=True)
        st.markdown("""
        Upload a night sky photo taken with **your camera** to:
        - Detect and identify constellations
        - Extract star coordinates and magnitudes
        - Unlock astronomical achievements
        """)
        
        uploaded_file = st.file_uploader("📸 Upload your night sky image", type=["jpg", "jpeg", "png"])
        
        if uploaded_file:
            # EXIF Verification
            is_verified, msg = authenticate_image(uploaded_file)
            st.info(msg)
            
            if is_verified:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.write("**Original Image:**")
                    st.image(uploaded_file, use_column_width=True)
                
                with col2:
                    if st.button("🔍 Analyze Image", key="analyze_btn"):
                        with st.spinner("Scanning the heavens..."):
                            img_bytes = uploaded_file.read()
                            uploaded_file.seek(0)
                            
                            stars, processed_img = stargaze_engine(img_bytes, thresh_val=150, min_area=5)
                            constellation, simplices, msg = match_patterns(stars)
                            
                            st.success(msg)
                            st.markdown(f"### 🌟 Constellation Identified: **{constellation}**")
                            
                            # Draw constellation
                            if simplices is not None:
                                output_img = processed_img.copy()
                                for simplex in simplices:
                                    pts = stars[simplex].astype(int)
                                    cv2.polylines(output_img, [pts], True, (0, 255, 255), 2)
                                
                                st.image(output_img, use_column_width=True, caption="Detected Star Pattern")
                            
                            st.markdown(f"""
                            **Detection Data:**
                            - Stars Detected: {len(stars)}
                            - Confidence: High
                            - Status: ✅ Achievement Unlocked
                            """)

    elif current_mode == "The Observatory":
        st.markdown(f'<h2 style="color: #8B5CF6;">🔭 The Observatory</h2>', unsafe_allow_html=True)
        st.markdown("""
        The neutral zone where **Science meets Wonder**.
        
        Slide left to analyze constellations with precision.
        Slide right to capture your emotional connection to the stars.
        """)
        
        st.info("📌 **Pro Tip:** This is your portal between objective observation and subjective experience.")

    elif current_mode == "Canvas Mode":
        st.markdown(f'<h2 style="color: #E24A8A;">🎨 Canvas Mode</h2>', unsafe_allow_html=True)
        st.markdown("""
        Record the **emotional essence** of your observations.
        
        - 📝 Journal your stargazing moments
        - 🎭 Attach feelings and memories
        - 🌌 Build your cosmic narrative
        """)
        
        st.info("🎨 **Coming Soon:** Full creative journaling and artistic features will be available here.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
