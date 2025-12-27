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

# 1. THE DIALOG (Moved to top to prevent NameError)
@st.dialog("Welcome to the Observatory! 🔭")
def welcome_popup():
    st.markdown("""
    ### Heyy Great To Have You Onboard! 🌌
    Welcome to **Stargaze**. This is the start to your sparkling experience ✨✨✨.
    
    **Your Journey:**
    2 Shades To the Experience
    Slide the Slidder 
    LEFT to enter a Astronomical Approach 
    RIGHT to enter a Creative Approach
    """)
    if st.button("Let's Start Mapping!"):
        st.session_state.has_seen_intro = True
        st.rerun()

# 2. PAGE SETUP & ARTISTIC CSS
st.set_page_config(page_title="Stargaze", page_icon="🌌", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lobster&family=Inter:wght@400;700&display=swap');

    /* The Main Background */
    .stApp {
        background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1280px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg");
        background-attachment: fixed;
        background-size: cover;
    }

    /* Night Sky Header with Sparkles */
    .sky-header {
        background: linear-gradient(180deg, #000000 0%, #060b26 70%, #0c1445 100%);
        padding: 50px;
        text-align: center;
        border-bottom: 3px solid #4A90E2;
        border-radius: 0 0 40px 40px;
        margin-bottom: 30px;
        position: relative;
    }

    /* SHOOTING STARS & SPARKLES */
    .shooting-star {
        position: absolute;
        top: 0; left: 80%;
        width: 3px; height: 3px;
        background: white;
        box-shadow: 0 0 15px 2px white;
        animation: shoot 5s linear infinite;
    }
    @keyframes shoot {
        0% { transform: translateX(0) translateY(0); opacity: 1; }
        15% { transform: translateX(-500px) translateY(500px); opacity: 0; }
        100% { opacity: 0; }
    }

    .sparkle {
        position: absolute;
        background: white;
        border-radius: 50%;
        animation: twinkle 2s ease-in-out infinite;
    }
    @keyframes twinkle {
        0%, 100% { opacity: 0.3; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.2); }
    }

    /* TYPOGRAPHY */
    h1 { font-family: 'Lobster', cursive !important; font-size: 4rem !important; color: #f0f0f0 !important; }
    
    /* Clean font for labels and inputs */
    label, p, .stButton, .stTabs, .stTextInput {
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
    }

    /* TAB HIGHLIGHTING */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(0, 0, 0, 0.7);
        padding: 10px;
        border-radius: 15px;
    }

    /* Glassmorphism Forms */
    [data-testid="stForm"] {
        background: rgba(0, 0, 0, 0.8) !important;
        backdrop-filter: blur(20px);
        border-radius: 30px !important;
        border: 1px solid rgba(74, 144, 226, 0.3) !important;
        padding: 40px !important;
    }
    </style>
    
    <div class="sky-header">
        <div class="shooting-star"></div>
        <div class="sparkle" style="top:20%; left:10%; width:2px; height:2px;"></div>
        <div class="sparkle" style="top:50%; left:85%; width:3px; height:3px;"></div>
        <h1>Stargaze</h1>
        <p style="font-family: 'Inter', sans-serif; letter-spacing: 2px;">WHERE ART MEETS THE INFINITE</p>
    </div>
    """, unsafe_allow_html=True)

# 3. SESSION LOGIC
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if st.session_state.logged_in:
    if st.sidebar.button("✨ Leave the Observatory"):
        st.session_state.logged_in = False
        st.session_state.has_seen_intro = False
        st.rerun()

# 4. ACCESS GATE
if not st.session_state.logged_in:
    login_tab, signup_tab = st.tabs(["🔒 Resume Exploration", "🚀 Begin Journey"])

    with signup_tab:
        with st.form("reg"):
            st.write("### Create Your Profile")
            email = st.text_input("Email Address")
            name = st.text_input("Preferred Name")
            pw = st.text_input("Security Key (Password)", type="password")
            if st.form_submit_button("Initialize Profile"):
                if is_valid_email(email) and len(pw) >= 6:
                    hashed = hash_pass(pw)
                    supabase.table("users").insert({"username": email, "name": name, "password_hash": hashed}).execute()
                    st.success("Your record is written in the stars. Please Log In.")
                else: st.error("The cosmos requires a valid email and 6+ character password.")

    with login_tab:
        with st.form("log"):
            st.write("### Enter the Observatory")
            u = st.text_input("Email")
            p = st.text_input("Security Key", type="password")
            if st.form_submit_button("Authenticate"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and check_pass(p, res.data[0]['password_hash']):
                    st.session_state.logged_in = True
                    st.session_state.user = res.data[0]
                    st.rerun()
                else: st.error("Authentication Failed: Credentials not recognized.")

# 5. DASHBOARD
else:
    if "has_seen_intro" not in st.session_state:
        welcome_popup()

    st.sidebar.markdown(f"## Welcome back, {st.session_state.user['name']} ✨")
    
    mode = st.select_slider(
        "Adjust Your Lens",
        options=["Science Hub", "The Observatory", "Creative Gallery"],
        value="The Observatory"
    )

    if mode == "Science Hub":
        st.markdown("<style>.main { background: #0b0d12 !important; }</style>", unsafe_allow_html=True)
        st.title("🔬 Technical Analysis")
        # Science content...
        
    elif mode == "Creative Gallery":
        st.markdown("<style>.main { background: #1a1a2e !important; }</style>", unsafe_allow_html=True)
        st.title("🎨 Celestial Gallery")
        # Art content...

    else:
        st.title("🌌 Main Observatory Feed")
        uploaded = st.file_uploader("Upload Star Photo", type=['jpg', 'jpeg', 'png'])

        if uploaded:
            stars, img = stargaze_engine(uploaded.read(), 120, 4)
            winner, geom, status = match_patterns(stars)
            
            col1, col2 = st.columns(2)
            with col1:
                st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption="Raw Input")
            with col2:
                if winner: st.success(f"Pattern Verified: {winner}")
                else: st.info(status)
