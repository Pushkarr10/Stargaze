import pandas as pd
import numpy as np
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st
from PIL import Image
import os

# --- 1. DATA LOADING ---
@st.cache_data
def load_star_data():
    df = pd.read_csv("stars.csv.gz", compression='gzip', usecols=['id', 'proper', 'ra', 'dec', 'mag'])
    df = df.dropna(subset=['id'])
    # Force IDs to be integers
    df['id'] = df['id'].astype(int)
    bright_stars = df[df['mag'] < 6.0].copy()
    bright_stars['proper'] = bright_stars['proper'].fillna('HIP ' + bright_stars['id'].astype(str))
    return bright_stars

@st.cache_resource
def load_ephemeris():
    return load('de421.bsp')

# --- 2. CALCULATOR ---
def calculate_sky_positions(df, lat, lon, custom_time=None):
    ts = load.timescale()
    t = ts.from_datetime(custom_time) if custom_time else ts.now()
    planets = load_ephemeris()
    earth = planets['earth']
    observer = earth + wgs84.latlon(lat, lon)
    stars = Star(ra_hours=df['ra'], dec_degrees=df['dec'])
    astrometric = observer.at(t).observe(stars)
    alt, az, distance = astrometric.apparent().altaz()
    df['altitude'] = alt.degrees
    df['azimuth'] = az.degrees
    return df[df['altitude'] > 0]

# --- 3. CONSTELLATION DATABASE ---
CONSTELLATIONS = {
    "Orion": [(27989, 25336), (25336, 24436), (24436, 27366), (27366, 27989), (27989, 28614), (26311, 26727), (26727, 25930), (25930, 25336), (26311, 27366)],
    "Ursa Major": [(54061, 53910), (53910, 58001), (58001, 59774), (59774, 54061), (59774, 62956), (62956, 65378), (65378, 67301)],
    "Cassiopeia": [(11569, 94263), (94263, 4427), (4427, 2685), (2685, 8886)],
    "Crux": [(60718, 62434), (62434, 59747), (59747, 58120), (58120, 60718)]
}

def add_constellations(fig, visible_stars_df):
    
    # --- DIAGNOSTIC: BETELGEUSE DETECTOR ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Constellation Debug")
    
    # 1. Search for Betelgeuse by Name
    betelgeuse = visible_stars_df[visible_stars_df['proper'].str.contains("Betelgeuse", case=False, na=False)]
    
    if not betelgeuse.empty:
        real_id = betelgeuse.iloc[0]['id']
        st.sidebar.success(f"✅ Found 'Betelgeuse' (ID: {real_id})")
        # Check if this ID matches our expectation (27989)
        if real_id != 27989:
            st.sidebar.error(f"⚠️ ID MISMATCH! Expected 27989, got {real_id}.")
    else:
        st.sidebar.warning("❌ 'Betelgeuse' not found in visible sky.")

    # --- MAIN DRAWING LOGIC ---
    star_map = {}
    for index, row in visible_stars_df.iterrows():
        try:
            star_map[int(row['id'])] = {'altitude': row['altitude'], 'azimuth': row['azimuth']}
        except: continue

    lines_drawn = 0
    for name, pairs in CONSTELLATIONS.items():
        x_lines, y_lines, z_lines = [], [], []
        has_lines = False
        
        for hip1, hip2 in pairs:
            if hip1 in star_map and hip2 in star_map:
                s1, s2 = star_map[hip1], star_map[hip2]
                for s in [s1, s2]:
                    alt, az = np.radians(s['altitude']), np.radians(s['azimuth'])
                    x_lines.append(100 * np.cos(alt) * np.sin(az))
                    y_lines.append(100 * np.cos(alt) * np.cos(az))
                    z_lines.append(100 * np.sin(alt))
                x_lines.append(None); y_lines.append(None); z_lines.append(None)
                has_lines = True
                lines_drawn += 1
        
        if has_lines:
            fig.add_trace(go.Scatter3d(
                x=x_lines, y=y_lines, z=z_lines, mode='lines',
                line=dict(color='#00FFFF', width=5), name=name, hoverinfo='name'
            ))

    st.sidebar.write(f"**Constellation Lines:** {lines_drawn}")
    
    # --- PROOF OF CONCEPT: CALIBRATION LASER ---
    # This draws a Green line from North Horizon to South Horizon.
    # If you see this, the "Simulation Limit" theory is wrong.
    fig.add_trace(go.Scatter3d(
        x=[0, 0], y=[100, -100], z=[0, 0],
        mode='lines',
        line=dict(color='#00FF00', width=10),
        name='Calibration Laser'
    ))
    
    return fig

# --- 4. IMAGE PROCESSOR ---
@st.cache_data
def process_terrain_mesh(filename, resolution=300):
    xy = np.linspace(-100, 100, resolution)
    x_grid, y_grid = np.meshgrid(xy, xy)
    radius = np.sqrt(x_grid**2 + y_grid**2)
    mask = radius <= 100
    x_flat, y_flat, z_flat = x_grid[mask], y_grid[mask], np.full_like(x_grid[mask], -2)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, filename)

    try:
        if not os.path.exists(file_path): return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(50,50,50)', dtype=object)
        img = Image.open(file_path).transpose(Image.FLIP_LEFT_RIGHT)
        w, h = img.size; m = min(w, h)
        img = img.crop(((w-m)/2, (h-m)/2, (w+m)/2, (h+m)/2)).resize((resolution, resolution))
        arr = np.array(img)
        R, G, B = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        color_grid = np.char.add(np.char.add(np.char.add('rgb(', R.astype(str)), ','), G.astype(str))
        color_grid = np.char.add(np.char.add(color_grid, ','), B.astype(str))
        color_grid = np.char.add(color_grid, ')')
        return x_flat, y_flat, z_flat, color_grid[mask]
    except: return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(50,50,50)', dtype=object)

# --- 5. RAILING ---
def generate_railing():
    z_rail = np.linspace(-2, 5, 5)
    theta_rail = np.linspace(0, 2*np.pi, 100)
    z_grid, theta_grid = np.meshgrid(z_rail, theta_rail)
    return 99 * np.cos(theta_grid), 99 * np.sin(theta_grid), z_grid

# --- 6. CHART GENERATOR ---
def create_3d_sphere_chart(visible_stars, show_constellations=False):
    alt_rad = np.radians(visible_stars['altitude'])
    az_rad = np.radians(visible_stars['azimuth'])
    r_sphere = 100 
    x = r_sphere * np.cos(alt_rad) * np.sin(az_rad)
    y = r_sphere * np.cos(alt_rad) * np.cos(az_rad)
    z = r_sphere * np.sin(alt_rad)
    
    fig = go.Figure()
    x_f, y_f, z_f, c_f = process_terrain_mesh("terrain.png", resolution=300)
    fig.add_trace(go.Mesh3d(x=x_f, y=y_f, z=z_f, vertexcolor=c_f, name='Floor', opacity=1, hoverinfo='skip'))
    
    x_r, y_r, z_r = generate_railing()
    fig.add_trace(go.Surface(x=x_r, y=y_r, z=z_r, colorscale=[[0,'#00d2ff'],[1,'#000510']], opacity=0.6, showscale=False))

    fig.add_trace(go.Scatter3d(x=[0,90,0,-90], y=[90,0,-90,0], z=[-1.5]*4, mode='text', text=["N","E","S","W"], textfont=dict(color=['#f33','#000','#000','#000'], size=30)))
    
    fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode='markers', marker=dict(size=np.clip(5-visible_stars['mag'],1,5), color='white', opacity=0.8), hovertext=visible_stars['proper']))
    
    if show_constellations:
        fig = add_constellations(fig, visible_stars)

    fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[-1], mode='markers', marker=dict(size=4, color='#0f0')))
    
    fig.update_layout(template="plotly_dark", scene=dict(bgcolor='#000510', xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False), dragmode="turntable"), margin=dict(l=0,r=0,b=0,t=0), height=500, showlegend=False)
    return fig

# --- 7. 2D CHART ---
def create_star_chart(visible_stars):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r = 90 - visible_stars['altitude'], theta = visible_stars['azimuth'], mode = 'markers', marker = dict(size = np.clip(12 - visible_stars['mag'] * 1.5, 0.5, 12), color = 'white', opacity = 0.8), hovertext = visible_stars['proper']))
    fig.update_layout(template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black', polar=dict(bgcolor="#000510", radialaxis=dict(visible=False, range=[0, 90]), angularaxis=dict(rotation=90, direction="clockwise")), showlegend=False, dragmode=False, margin=dict(l=20, r=20, t=20, b=20), height=500)
    for a, l in [(0,"N"),(90,"E"),(180,"S"),(270,"W")]: fig.add_annotation(x=a, y=1.1, text=f"<b>{l}</b>", showarrow=False, font=dict(color="#888"))
    return fig
