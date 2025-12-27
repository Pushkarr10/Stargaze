import streamlit as st
import cv2
import numpy as np
import streamlit_authenticator as stauth
import json
from scipy.spatial import Delaunay

# ==========================================
# PHASE 1: THE CELESTIAL ENGINE (The Backbone)
# ==========================================

def stargaze_engine(img_bytes, thresh_val, min_area):
    """Detects stars in the uploaded image."""
    file_bytes = np.asarray(bytearray(img_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Enhancement & Noise Removal
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    _, thresh = cv2.threshold(enhanced, thresh_val, 255, cv2.THRESH_BINARY)
    morphed = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((2,2), np.uint8))
    
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(morphed)
    stars = np.array([centroids[i] for i in range(1, num_labels) if min_area < stats[i, cv2.CC_STAT_AREA] < 100])
    return stars, img

def match_patterns(stars, db_path='lookup_db.json'):
    """Matches detected stars against the geometric database."""
    try:
        with open(db_path, 'r') as f:
            db = json.load(f)
    except: return None, None, "Database (lookup_db.json) not found."
    
    if len(stars) < 4: return None, None, "Need more stars for a match."
    
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
# PHASE 2: UI DESIGN & AUTH (The New Shell)
# ==========================================

st.set_page_config(page_title="Stargaze AI", page_icon="🌌", layout="wide")

# Custom CSS for the 'Night Sky' look
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { border-radius: 20px; background-color: #4A90E2; color: white; }
    </style>
    """, unsafe_allow_code=True)

# Login Credentials
names = ['Pushkar']
usernames = ['pushkar']
passwords = ['stargaze123']

authenticator = stauth.Authenticate(names, usernames, passwords, 
    'stargaze_cookie', 'signature_key', cookie_expiry_days=30)

name, authentication_status, username = authenticator.login('Login', 'main')

# ==========================================
# PHASE 3: THE PROTECTED APP EXPERIENCE
# ==========================================

if authentication_status:
    authenticator.logout('Logout', 'sidebar')
    st.sidebar.title(f"Welcome, {name} ✨")
    
    st.title("🌌 Stargaze: AI Celestial Mapper")
    
    with st.sidebar:
        st.divider()
        st.header("⚙️ Image Processing")
        t_val = st.slider("Sensitivity", 10, 255, 120)
        a_min = st.slider("Min Star Size (px)", 1, 10, 4)

    uploaded = st.file_uploader("Upload Sky Photo", type=['jpg', 'png', 'jpeg'])

    if uploaded:
        with st.spinner("Analyzing the deep sky..."):
            stars, original = stargaze_engine(uploaded.read(), t_val, a_min)
            winner, geometry, status = match_patterns(stars)
            
            col1, col2 = st.columns(2)
            with col1:
                st.image(cv2.cvtColor(original, cv2.COLOR_BGR2RGB), caption="Raw Input")
            with col2:
                if winner:
                    st.success(f"Constellation Identified: {winner}")
                    for s in geometry:
                        cv2.polylines(original, [stars[s].astype(int)], True, (0, 255, 255), 2)
                    st.image(cv2.cvtColor(original, cv2.COLOR_BGR2RGB), caption="Identified Pattern")
                else:
                    st.error(status)

elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your credentials to access the observatory.')
