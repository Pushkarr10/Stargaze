import streamlit as st
from supabase import create_client, Client
import bcrypt
import cv2
import numpy as np
import json
from scipy.spatial import Delaunay

# ==========================================
# ZONE 1: THE BACKBONE (Your Initial Code)
# ==========================================
# We keep these functions exactly as they were, so the "math" never breaks.

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

# ==========================================
# ZONE 2: THE BRAIN (Database & Auth)
# ==========================================

supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def hash_pass(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def check_pass(p, h): return bcrypt.checkpw(p.encode(), h.encode())

# ==========================================
# ZONE 3: THE INTERFACE (User Experience)
# ==========================================

st.set_page_config(page_title="Stargaze AI", page_icon="🌌", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- LOGOUT LOGIC ---
if st.session_state.logged_in:
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

# --- THE LOGIN/SIGNUP GATE ---
if not st.session_state.logged_in:
    st.title("🌌 Stargaze AI")
    st.info("Welcome to the community observatory. Please sign in to begin mapping.")
    
    choice = st.radio("Select Action", ["Login", "Sign Up"], horizontal=True)
    
    if choice == "Sign Up":
        with st.form("signup"):
            u = st.text_input("Username")
            n = st.text_input("Name")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Create Account"):
                supabase.table("users").insert({"username": u, "name": n, "password_hash": hash_pass(p)}).execute()
                st.success("Welcome aboard! Switch to Login to enter.")
                
    else:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Enter Observatory"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and check_pass(p, res.data[0]['password_hash']):
                    st.session_state.logged_in = True
                    st.session_state.user = res.data[0]
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

# --- THE MAIN APP (Only visible if logged in) ---
else:
    st.title(f"🔭 {st.session_state.user['name']}'s Observatory")
    
    with st.sidebar:
        st.header("⚙️ Controls")
        t_val = st.slider("Sensitivity", 10, 255, 120)
        a_min = st.slider("Min Star Size", 1, 10, 4)
        
    uploaded = st.file_uploader("Upload Star Photo", type=['jpg', 'jpeg', 'png'])
    
    if uploaded:
        # HERE IS WHERE WE CALL YOUR ORIGINAL CODE!
        stars, original = stargaze_engine(uploaded.read(), t_val, a_min)
        winner, geometry, status = match_patterns(stars)
        
        # Display results...
        # [Remaining image display code here]
