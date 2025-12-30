import pandas as pd
import numpy as np
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st
from PIL import Image
import os

# --- 1. DATA LOADING (Cached & Cleaned) ---
@st.cache_data
def load_star_data():
    # Load raw data
    df = pd.read_csv("stars.csv.gz", compression='gzip', usecols=['id', 'proper', 'ra', 'dec', 'mag'])
    
    # Drop rows with no ID
    df = df.dropna(subset=['id'])
    df['id'] = df['id'].astype(int)
    
    # Filter for visible stars (Mag < 6.0)
    bright_stars = df[df['mag'] < 6.0].copy()
    
    # Fill missing names with HIP ID
    bright_stars['proper'] = bright_stars['proper'].fillna('HIP ' + bright_stars['id'].astype(str))
    
    # --- NORMALIZE NAMES ---
    # Convert to UPPERCASE and remove spaces for robust matching
    bright_stars['proper_clean'] = bright_stars['proper'].astype(str).str.upper().str.strip()
    
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
    # Return only stars above horizon
    return df[df['altitude'] > 0]

# --- 3. CONSTELLATION DATABASE (Refined Pairs) ---
# These pairs form the "classic" stick figures
CONSTELLATIONS = {
    "Orion (Hunter)": [
        ("BETELGEUSE", "MEISSA"), ("MEISSA", "BELLATRIX"),  # Shoulders / Head
        ("BETELGEUSE", "ALNITAK"), ("BELLATRIX", "MINTAKA"), # Body
        ("ALNITAK", "ALNILAM"), ("ALNILAM", "MINTAKA"),     # Belt
        ("ALNITAK", "SAIPH"), ("MINTAKA", "RIGEL"),         # Legs
        ("RIGEL", "SAIPH")                                  # Feet Connection (Optional)
    ],
    "Ursa Major (Big Dipper)": [
        ("DUBHE", "MERAK"), ("MERAK", "PHECDA"), ("PHECDA", "MEGREZ"), # The Cup
        ("MEGREZ", "DUBHE"), 
        ("MEGREZ", "ALIOTH"), ("ALIOTH", "MIZAR"), ("MIZAR", "ALKAID") # The Handle
    ],
    "Cassiopeia (The Queen)": [
        ("CAPH", "SCHEDAR"), ("SCHEDAR", "NAVI"), 
        ("NAVI", "RUCHBAH"), ("RUCHBAH", "SEGIN") # The 'W' Shape
    ],
    "Crux (Southern Cross)": [
        ("ACRUX", "GACRUX"),   # Long axis
        ("MIMOSA", "IMAI")     # Short axis (Cross bar)
    ],
    "Scorpius (Scorpion)": [
        ("ANTARES", "ALNIYAT"), ("ALNIYAT", "ACRAB"), # Head
        ("ACRAB", "DSCHUBBA"), 
        ("ANTARES", "WEI"), ("WEI", "SARGAS"),        # Body
        ("SARGAS", "SHAULA"), ("SHAULA", "LESATH")    # Tail/Stinger
    ],
    "Canis Major (Great Dog)": [
        ("SIRIUS", "MIRZAM"),  # Head
        ("SIRIUS", "MULIPHEIN"), 
        ("SIRIUS", "WEZEN"),   # Body
        ("WEZEN", "ADHARA"),   # Rear Leg
        ("WEZEN", "ALUDRA")    # Tail
    ],
    "Gemini (The Twins)": [
        ("POLLUX", "CASTOR"),  # The heads
        ("POLLUX", "WASAT"), ("WASAT", "ALZIRR"), # Twin 1 Body
        ("CASTOR", "MEBSUTA"), ("MEBSUTA", "TEJAT") # Twin 2 Body
    ]
}

def add_constellations(fig, visible_stars_df):
    """
    Draws constellation lines using robust UPPERCASE matching.
    """
    # Create lookup: Clean Name -> Data
    # Priority: If duplicates exist, we want the brightest star.
    # We sort by Magnitude (ascending = brighter) first.
    visible_stars_df = visible_stars_df.sort_values('mag', ascending=True)
    
    star_map = {}
    for index, row in visible_stars_df.iterrows():
        clean_name = row['proper_clean']
        # Only store the first (brightest) occurrence of a name
        if clean_name not in star_map:
            star_map[clean_name] = {'altitude': row['altitude'], 'azimuth': row['azimuth']}

    # Draw Lines
    for name, pairs in CONSTELLATIONS.items():
        x_lines, y_lines, z_lines = [], [], []
        has_lines = False
        
        for star1, star2 in pairs:
            # Check for substring matches (e.g. "BETELGEUSE" inside "ALPHA ORIONIS (BETELGEUSE)")
            # This is a bit slower but safer if names aren't exact.
            s1_data = None
            s2_data = None
            
            # Fast exact match first
            if star1 in star_map: s1_data = star_map[star1]
            if star2 in star_map: s2_data = star_map[star2]
            
            # Fallback: Search keys if exact match fails
            if not s1_data:
                for key in star_map:
                    if star1 in key: 
                        s1_data = star_map[key]; break
            if not s2_data:
                for key in star_map:
                    if star2 in key: 
                        s2_data = star_map[key]; break

            # If we found both ends of the stick
            if s1_data and s2_data:
                # Math
                for s in [s1_data, s2_data]:
                    alt, az = np.radians(s['altitude']), np.radians(s['azimuth'])
                    x_lines.append(100 * np.cos(alt) * np.sin(az))
                    y_lines.append(100 * np.cos(alt) * np.cos(az))
                    z_lines.append(100 * np.sin(alt))
                
                x_lines.append(None); y_lines.append(None); z_lines.append(None)
                has_lines = True
        
        if has_lines:
            fig.add_trace(go.Scatter3d(
                x=x_lines, y=y_lines, z=z_lines,
                mode='lines',
                line=dict(color='rgba(100, 255, 255, 0.4)', width=4), # Cyan, thinner for neatness
                name=name,
                hoverinfo='name'
            ))

    return fig

# --- 4. IMAGE PROCESSOR (Cached) ---
@st.cache_data
def process_terrain_mesh(filename, resolution=300):
    xy = np.linspace(-100, 100, resolution)
    x_grid, y_grid = np.meshgrid(xy, xy)
    
    radius = np.sqrt(x_grid**2 + y_grid**2)
    mask = radius <= 100
    
    x_flat = x_grid[mask]
    y_flat = y_grid[mask]
    z_flat = np.full_like(x_flat, -2) 
    
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
        return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(50,50,50)', dtype=object)

# --- 5. RAILING ---
def generate_railing():
    z_rail = np.linspace(-2, 5, 5)
    theta_rail = np.linspace(0, 2*np.pi, 100)
    z_grid_rail, theta_grid_rail = np.meshgrid(z_rail, theta_rail)
    x_rail = 99 * np.cos(theta_grid_rail)
    y_rail = 99 * np.sin(theta_grid_rail)
    return x_rail, y_rail, z_grid_rail

# --- 6. CHART GENERATOR ---
def create_3d_sphere_chart(visible_stars, show_constellations=False):
    alt_rad = np.radians(visible_stars['altitude'])
    az_rad = np.radians(visible_stars['azimuth'])
    r_sphere = 100 
    x = r_sphere * np.cos(alt_rad) * np.sin(az_rad)
    y = r_sphere * np.cos(alt_rad) * np.cos(az_rad)
    z = r_sphere * np.sin(alt_rad)
    
    fig = go.Figure()

    # (A) Floor
    x_f, y_f, z_f, c_f = process_terrain_mesh("terrain.png", resolution=300)
    fig.add_trace(go.Mesh3d(x=x_f, y=y_f, z=z_f, vertexcolor=c_f, name='Terrain Floor', hoverinfo='skip', opacity=1.0, delaunayaxis='z'))

    # (B) Railing
    x_r, y_r, z_r = generate_railing()
    fig.add_trace(go.Surface(x=x_r, y=y_r, z=z_r, colorscale=[[0, '#00d2ff'], [1, '#000510']], showscale=False, opacity=0.6, name='Horizon Wall', hoverinfo='skip'))

    # (C) Compass
    fig.add_trace(go.Scatter3d(
        x=[0, 90, 0, -90], y=[90, 0, -90, 0], z=[-1.5]*4,
        mode='text', text=["<b>N</b>", "<b>E</b>", "<b>S</b>", "<b>W</b>"],
        textfont=dict(color=['#ff3333', '#000510', '#000510', '#000510'], size=30, family="Arial Black"),
        hoverinfo='skip', name='Compass'
    ))

    # (D) Stars
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z, mode='markers',
        marker=dict(size=np.clip(5 - visible_stars['mag'], 1, 5), color='white', opacity=0.8, line=dict(width=0)),
        hovertext=visible_stars['proper'], name='Stars'
    ))

    # (E) Constellations (Name-Based Match)
    if show_constellations:
        fig = add_constellations(fig, visible_stars)

    # (F) Observer
    fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[-1], mode='markers', marker=dict(size=4, color='#00ff00'), name='Observer'))

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
    
    return fig

# --- 7. 2D CHART ---
def create_star_chart(visible_stars):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r = 90 - visible_stars['altitude'], theta = visible_stars['azimuth'], mode = 'markers', marker = dict(size = np.clip(12 - visible_stars['mag'] * 1.5, 0.5, 12), color = 'white', opacity = 0.8), hovertext = visible_stars['proper']))
    fig.update_layout(template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black', polar=dict(bgcolor="#000510", radialaxis=dict(visible=False, range=[0, 90]), angularaxis=dict(rotation=90, direction="clockwise")), showlegend=False, dragmode=False, margin=dict(l=20, r=20, t=20, b=20), height=500)
    for a, l in [(0,"N"),(90,"E"),(180,"S"),(270,"W")]: fig.add_annotation(x=a, y=1.1, text=f"<b>{l}</b>", showarrow=False, font=dict(color="#888"))
    return fig
