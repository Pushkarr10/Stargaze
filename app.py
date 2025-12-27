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
# ==========================================
# ZONE 3: THE INTERFACE (The Validated UX)
# ==========================================
import re # Add this at the very top of your file with other imports

st.set_page_config(page_title="Stargaze AI", page_icon="🌌", layout="wide")

# Helper: Email Pattern Validation
def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# CSS for the "Night Mode" Observatory feel
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { height: 50px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# Session Management
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- THE LOGIN & REGISTRATION GATE ---
if not st.session_state.logged_in:
    st.title("🌌 Stargaze AI: Digital Observatory")
    
    login_tab, signup_tab = st.tabs(["🔒 Log In", "🚀 Create Account"])

    # 1. SIGN UP TAB (With Professional Validation)
    with signup_tab:
        with st.form("registration_form", clear_on_submit=True):
            st.info("Enter your details to create a permanent explorer profile.")
            new_email = st.text_input("Email Address")
            full_name = st.text_input("Display Name")
            new_pass = st.text_input("Password", type="password", help="Minimum 6 characters")
            confirm_pass = st.text_input("Confirm Password", type="password")
            
            submit_reg = st.form_submit_button("Initialize Profile")
            
            if submit_reg:
                # --- VALIDATION LOGIC ---
                if not is_valid_email(new_email):
                    st.error("Invalid format. Please use a real email (e.g., name@mail.com).")
                elif len(full_name) < 2:
                    st.error("Please enter your full name.")
                elif len(new_pass) < 6:
                    st.error("Password too weak. Use at least 6 characters.")
                elif new_pass != confirm_pass:
                    st.error("Passwords do not match.")
                else:
                    try:
                        # Check for existing user first
                        existing = supabase.table("users").select("username").eq("username", new_email).execute()
                        if existing.data:
                            st.warning("This email is already registered. Head over to the login tab!")
                        else:
                            # Hashing and Saving to Supabase
                            hashed = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                            supabase.table("users").insert({
                                "username": new_email, 
                                "name": full_name, 
                                "password_hash": hashed
                            }).execute()
                            st.success(f"Welcome aboard, {full_name}! You can now log in.")
                    except Exception as e:
                        st.error("Observatory connection error. Please try again.")

    # 2. LOGIN TAB
    with login_tab:
        with st.form("login_form"):
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Enter Observatory"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and bcrypt.checkpw(p.encode(), res.data[0]['password_hash'].encode()):
                    st.session_state.logged_in = True
                    st.session_state.user = res.data[0]
                    st.rerun()
                else:
                    st.error("Access Denied: Invalid email or password.")
    
# --- THE MAIN APP EXPERIENCE (Only visible if logged in) ---
else:
    @st.dialog("Welcome to the Observatory! 🔭")
def welcome_popup():
    st.write("""
    ### Hey Explorer! 🌌
    Welcome to **Stargaze AI**, where we turn your blurry night-sky photos into actual maps of the cosmos.
    
    **How does it work?**
    1. **Star Spotting:** Our AI hunts for bright pixels (stars) and ignores the noise.
    2. **The Barcode:** It looks at the *angles* and *distances* between stars to create a unique geometric fingerprint.
    3. **The Match:** It compares that fingerprint against our ancient celestial database.
    
    *Tip: If the sky looks messy, use the **Sensitivity** slider in the sidebar to clean up the noise!*
    """)
    if st.button("Let's Start Mapping!"):
        st.rerun()

# --- Inside your 'Logged In' logic ---
if st.session_state.logged_in:
    # We use a session state 'has_seen_intro' so it only pops up once per login
    if "has_seen_intro" not in st.session_state:
        welcome_popup()
        st.session_state.has_seen_intro = True
    st.sidebar.title(f"🔭 {st.session_state.user['name']}")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()
    
    st.title("🌌 Stargaze AI: Pattern Matcher")
    
    with st.sidebar:
        st.divider()
        st.header("⚙️ Detection Controls")
        t_val = st.slider("Sensitivity (Threshold)", 10, 255, 120)
        a_min = st.slider("Min Star Size (px)", 1, 10, 4)
    
    uploaded = st.file_uploader("Upload Star Photo", type=['jpg', 'jpeg', 'png'])
    
    if uploaded:
        with st.spinner("Processing deep sky data..."):
            # CALLING YOUR ORIGINAL BACKBONE CODE
            stars, original = stargaze_engine(uploaded.read(), t_val, a_min)
            winner, geometry, status = match_patterns(stars)
            
            # Displaying the results side-by-side
            col1, col2 = st.columns(2)
            with col1:
                st.image(cv2.cvtColor(original, cv2.COLOR_BGR2RGB), caption="Raw Capture")
            with col2:
                if winner:
                    st.success(f"Pattern Identified: {winner}")
                    for s in geometry:
                        cv2.polylines(original, [stars[s].astype(int)], True, (0, 255, 255), 2)
                    st.image(cv2.cvtColor(original, cv2.COLOR_BGR2RGB), caption="Constellation Overlay")
                else:
                    st.error(f"Analysis: {status}")
