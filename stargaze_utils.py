import pandas as pd
import numpy as np
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st
from PIL import Image
import os
# --- CONSTELLATION DATABASE ---
CONSTELLATIONS = {
    "Orion": [(27989, 25336), (25336, 24436), (24436, 27366), (27366, 27989), (27989, 28614), (26311, 26727), (26727, 25930), (25930, 25336), (26311, 27366)],
    "Ursa Major": [(54061, 53910), (53910, 58001), (58001, 59774), (59774, 54061), (59774, 62956), (62956, 65378), (65378, 67301)],
    "Ursa Minor": [(11767, 85822), (85822, 82080), (82080, 77055), (77055, 72607), (72607, 75097), (75097, 82080)],
    "Cassiopeia": [(11569, 94263), (94263, 4427), (4427, 2685), (2685, 8886)],
    "Cygnus": [(102098, 99639), (99639, 95947), (100453, 99639), (99639, 97165)],
    "Scorpius": [(80763, 78820), (78820, 78401), (80763, 81266), (81266, 82396), (82396, 82514), (82514, 84143), (84143, 86228), (86228, 87073), (87073, 86670), (86670, 85927), (85927, 85696)],
    "Leo": [(49669, 50583), (50583, 54872), (54872, 57632), (54872, 54879), (54879, 49669), (49669, 49583), (49583, 50583), (50583, 50335), (50335, 48455), (48455, 47908)],
    "Gemini": [(37826, 35550), (35550, 33694), (33694, 30343), (36850, 32246), (32246, 31681), (31681, 29655)],
    "Taurus": [(21421, 20205), (20205, 20889), (20889, 20894), (20894, 21421), (20889, 17702), (21421, 25428), (21421, 24847)],
    "Canis Major": [(32349, 31425), (32349, 33579), (32349, 33165), (33165, 33977), (33165, 35904)],
    "Crux": [(60718, 62434), (62434, 59747), (59747, 58120), (58120, 60718)]
}

def add_constellations(fig, visible_stars_df):
    """
    Draws lines and prints DEBUG info to find out why lines are missing.
    """
    # 1. DEBUG: Check if we have IDs
    # If the ID column is missing or weird, this will tell us.
    if 'id' not in visible_stars_df.columns:
        print("❌ ERROR: 'id' column missing from visible_stars dataframe!")
        return fig

    # 2. DEBUG: check the first ID
    first_id = visible_stars_df['id'].iloc[0]
    print(f"ℹ️ DEBUG: First Star ID is {first_id} (Type: {type(first_id)})")

    # Create the lookup map
    star_map = visible_stars_df.set_index('id')[['altitude', 'azimuth']].to_dict('index')
    
    lines_drawn_count = 0

    for name, pairs in CONSTELLATIONS.items():
        x_lines, y_lines, z_lines = [], [], []
        has_visible_lines = False
        
        for hip1, hip2 in pairs:
            # Check matches
            if hip1 in star_map and hip2 in star_map:
                s1 = star_map[hip1]
                s2 = star_map[hip2]
                
                # Math to draw the line
                for s in [s1, s2]:
                    alt, az = np.radians(s['altitude']), np.radians(s['azimuth'])
                    x_lines.append(100 * np.cos(alt) * np.sin(az))
                    y_lines.append(100 * np.cos(alt) * np.cos(az))
                    z_lines.append(100 * np.sin(alt))
                
                # Break the line
                x_lines.append(None)
                y_lines.append(None)
                z_lines.append(None)
                has_visible_lines = True
                lines_drawn_count += 1
        
        if has_visible_lines:
            print(f"✅ Drawing {name}...")
            fig.add_trace(go.Scatter3d(
                x=x_lines, y=y_lines, z=z_lines,
                mode='lines',
                # INCREASED WIDTH AND OPACITY to make them super obvious
                line=dict(color='#00FFFF', width=10), 
                name=name,
                hoverinfo='name'
            ))
            
    if lines_drawn_count == 0:
        print("⚠️ WARNING: No constellation lines matched visible stars.")
    else:
        print(f"🎉 Success: Drew {lines_drawn_count} lines.")

    return fig
# --- 1. CACHED DATA LOADING (The Speed Fix) ---
@st.cache_data

def load_star_data():
    # Load raw data
    df = pd.read_csv("stars.csv.gz", compression='gzip', usecols=['id', 'proper', 'ra', 'dec', 'mag'])
    
    # --- CRITICAL FIX START ---
    # 1. Drop rows that have no ID at all
    df = df.dropna(subset=['id'])
    
    # 2. Force IDs to be Integers (e.g., converts 27989.0 -> 27989)
    # This ensures they match the keys in our Constellation Dictionary
    df['id'] = df['id'].astype(int)
    # --- CRITICAL FIX END ---
    
    # Filter for bright stars
    bright_stars = df[df['mag'] < 6.0].copy()
    
    # Fill missing names
    bright_stars['proper'] = bright_stars['proper'].fillna('HIP ' + bright_stars['id'].astype(str))
    
    return bright_stars
@st.cache_resource
def load_ephemeris():
    """Loads heavy planetary data ONCE (Fixes slider lag)."""
    return load('de421.bsp')

# --- 2. CALCULATOR (Now Optimized) ---
def calculate_sky_positions(df, lat, lon, custom_time=None):
    ts = load.timescale()
    t = ts.from_datetime(custom_time) if custom_time else ts.now()

    # Use the Cached Ephemeris (Fast!)
    planets = load_ephemeris()
    earth = planets['earth']
    
    observer = earth + wgs84.latlon(lat, lon)
    stars = Star(ra_hours=df['ra'], dec_degrees=df['dec'])
    
    astrometric = observer.at(t).observe(stars)
    alt, az, distance = astrometric.apparent().altaz()
    
    df['altitude'] = alt.degrees
    df['azimuth'] = az.degrees
    return df[df['altitude'] > 0]

# --- 3. 2D CHART ---
def create_star_chart(visible_stars):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r = 90 - visible_stars['altitude'],
        theta = visible_stars['azimuth'],
        mode = 'markers',
        marker = dict(
            size = np.clip(12 - visible_stars['mag'] * 1.5, 0.5, 12),
            color = 'white',
            opacity = np.clip(1.2 - (visible_stars['mag'] / 6), 0.3, 1.0),
            line = dict(width=0)
        ),
        hovertext = visible_stars['proper'],
        hoverinfo = "text"
    ))
    fig.update_layout(
        template = "plotly_dark",
        paper_bgcolor = 'black', plot_bgcolor = 'black',
        polar = dict(
            bgcolor = "#000510",
            radialaxis = dict(visible = False, range = [0, 90]),
            angularaxis = dict(
                visible = True, showline = True, linecolor = "#444", 
                showgrid = False, showticklabels = False, 
                direction = "clockwise", rotation = 90
            )
        ),
        dragmode = False, showlegend = False,
        margin = dict(l=20, r=20, t=20, b=20), height = 500
    )
    directions = [(0, "N"), (90, "E"), (180, "S"), (270, "W")]
    for angle, label in directions:
        fig.add_annotation(x=angle, y=1.1, text=f"<b>{label}</b>", showarrow=False, font=dict(color="#888"))
    return fig

# --- 4. IMAGE PROCESSOR (Cached for Speed) ---
@st.cache_data
def process_terrain_mesh(filename, resolution=300):
    """Generates texture mesh. Cached so we don't process images every frame."""
    xy = np.linspace(-100, 100, resolution)
    x_grid, y_grid = np.meshgrid(xy, xy)
    
    radius = np.sqrt(x_grid**2 + y_grid**2)
    mask = radius <= 100
    
    x_flat = x_grid[mask]
    y_flat = y_grid[mask]
    z_flat = np.full_like(x_flat, -2) 
    
    # Robust Path Finding
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, filename)

    try:
        if not os.path.exists(file_path):
            return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(50,50,50)', dtype=object)
            
        img = Image.open(file_path)
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim)/2
        top = (height - min_dim)/2
        right = (width + min_dim)/2
        bottom = (height + min_dim)/2
        img = img.crop((left, top, right, bottom))
        
        img = img.resize((resolution, resolution))
        img_array = np.array(img)
        R, G, B = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        
        color_grid = np.char.add(np.char.add(np.char.add('rgb(', R.astype(str)), ','), G.astype(str))
        color_grid = np.char.add(np.char.add(color_grid, ','), B.astype(str))
        color_grid = np.char.add(color_grid, ')')
        
        return x_flat, y_flat, z_flat, color_grid[mask]
        
    except Exception as e:
        # We can't use st.error inside a cached function easily, so just print
        print(f"Texture Error: {e}")
        return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(50,50,50)', dtype=object)

# --- 5. RAILING GENERATOR ---
def generate_railing():
    z_rail = np.linspace(-2, 5, 5)
    theta_rail = np.linspace(0, 2*np.pi, 100)
    z_grid_rail, theta_grid_rail = np.meshgrid(z_rail, theta_rail)
    x_rail = 99 * np.cos(theta_grid_rail)
    y_rail = 99 * np.sin(theta_grid_rail)
    return x_rail, y_rail, z_grid_rail

# --- 6. 3D CHART GENERATOR ---
def create_3d_sphere_chart(visible_stars, show_constellations=False):
    # A. Star Math
    alt_rad = np.radians(visible_stars['altitude'])
    az_rad = np.radians(visible_stars['azimuth'])
    r_sphere = 100 
    x = r_sphere * np.cos(alt_rad) * np.sin(az_rad)
    y = r_sphere * np.cos(alt_rad) * np.cos(az_rad)
    z = r_sphere * np.sin(alt_rad)
    
    fig = go.Figure()

    # B. Textured Floor (Cached!)
    x_f, y_f, z_f, c_f = process_terrain_mesh("terrain.png", resolution=300)
    fig.add_trace(go.Mesh3d(
        x=x_f, y=y_f, z=z_f, vertexcolor=c_f, 
        name='Terrain Floor', hoverinfo='skip', opacity=1.0, delaunayaxis='z' 
    ))

    # C. Railing
    x_r, y_r, z_r = generate_railing()
    fig.add_trace(go.Surface(
        x=x_r, y=y_r, z=z_r, colorscale=[[0, '#00d2ff'], [1, '#000510']], 
        showscale=False, opacity=0.6, name='Horizon Wall', hoverinfo='skip'
    ))

    # D. Compass
    fig.add_trace(go.Scatter3d(
        x=[0, 90, 0, -90], y=[90, 0, -90, 0], z=[-1.5, -1.5, -1.5, -1.5],
        mode='text', text=["<b>N</b>", "<b>E</b>", "<b>S</b>", "<b>W</b>"],
        textfont=dict(color=['#ff3333', '#000510', '#000510', '#000510'], size=30, family="Arial Black"),
        hoverinfo='skip', name='Compass'
    ))

    # E. Stars & Observer
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z, mode='markers',
        marker=dict(size=np.clip(5 - visible_stars['mag'], 1, 5), color='white', opacity=0.8, line=dict(width=0)),
        hovertext=visible_stars['proper'], name='Stars'
    ))
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[-1], mode='markers', marker=dict(size=4, color='#00ff00'), name='Observer'
    ))

    # F. Layout
    fig.update_layout(
        template="plotly_dark",
        scene=dict(
            bgcolor='#000510',
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            dragmode="turntable", 
            camera=dict(eye=dict(x=0.1, y=-0.1, z=0.1), up=dict(x=0, y=0, z=1))
        ),
        showlegend=False, margin=dict(l=0, r=0, b=0, t=0), height=500
    )
    # In stargaze_utils.py
# ... (Your existing stars/observer/layout code is here) ...

    # --- ADD THIS NEW BLOCK ---
    if show_constellations:
        fig = add_constellations(fig, visible_stars)
    # --------------------------

    return fig
    
