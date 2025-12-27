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

st.set_page_config(page_title="Stargaze AI", page_icon="🌌", layout="wide")

@st.dialog("Welcome to the Observatory! 🔭")
def welcome_popup():
    st.write("""
    ### Hey Explorer! 🌌
    Welcome to **Stargaze AI**. You are now part of a community that turns curiosity into celestial maps.
    
    **Your Journey:**
    1. **Verify:** Use the Science Hub to ensure your capture is genuine.
    2. **Analyze:** Let the Geometric Engine find the patterns.
    3. **Collect:** Build your personal library of the cosmos.
    """)
    if st.button("Enter the Observatory"):
        st.session_state.has_seen_intro = True
        st.rerun()

if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🌌 Stargaze AI")
    login_tab, signup_tab = st.tabs(["🔒 Log In", "🚀 Create Account"])

    with signup_tab:
        with st.form("reg"):
            email = st.text_input("Email")
            name = st.text_input("Display Name")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Join Observatory"):
                if is_valid_email(email) and len(pw) >= 6:
                    hashed = hash_pass(pw)
                    supabase.table("users").insert({"username": email, "name": name, "password_hash": hashed}).execute()
                    st.success("Account Ready! Please Log In.")
                else: st.error("Invalid details provided.")

    with login_tab:
        with st.form("log"):
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Enter"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and check_pass(p, res.data[0]['password_hash']):
                    st.session_state.logged_in = True
                    st.session_state.user = res.data[0]
                    st.rerun()
                else: st.error("Invalid Credentials.")

else:
    # --- LOGGED IN DASHBOARD ---
    if "has_seen_intro" not in st.session_state:
        welcome_popup()

    st.sidebar.title(f"🔭 {st.session_state.user['name']}")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

    # -----------------------------------------------------------------
    # MODULE A: DUAL-ZONE SWITCHER (Science vs. Creative)
    # -----------------------------------------------------------------
    # This is where we will put the "Torn UI" toggle code.
    
    st.title("Main Observatory Feed")
    uploaded = st.file_uploader("Upload Star Photo", type=['jpg', 'jpeg', 'png'])

    if uploaded:
        # -----------------------------------------------------------------
        # MODULE B: AUTHENTICATION & PROCESSING
        # -----------------------------------------------------------------
        # This is where we will put the EXIF Check and Image Enhancement.
        
        stars, img = stargaze_engine(uploaded.read(), 120, 4)
        winner, geom, status = match_patterns(stars)
        
        if winner: st.success(f"Identified: {winner}")
        else: st.info(status)
        st.image(img, channels="BGR")
