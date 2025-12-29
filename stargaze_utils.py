import pandas as pd
import numpy as np
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st
from PIL import Image
import os

# --- 1. DATA LOADING (Cached) ---
@st.cache_data
def load_star_data():
    # Load raw data
    df = pd.read_csv("stars.csv.gz", compression='gzip', usecols=['id', 'proper', 'ra', 'dec', 'mag'])
    
    # Drop rows with no ID to keep data clean
    df = df.dropna(subset=['id'])
    df['id'] = df['id'].astype(int)
    
    # Filter for visible stars
    bright_stars = df[df['mag'] < 6.0].copy()
    
    # Ensure every star has a name (fallback to HIP ID if name is missing)
    bright_stars['proper'] = bright_stars['proper'].fillna('HIP ' + bright_stars['id'].astype(str))
    
    # Standardize names (Capitalize) to ensure matching works
    bright_stars['proper'] = bright_stars['proper'].str.strip()
    
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

# --- 3. CONSTELLATION DATABASE (BY NAME) ---
# We use Names instead of IDs to avoid database mismatches
CONSTELLATIONS = {
    "Orion": [
        ("Betelgeuse", "Bellatrix"), ("Bellatrix", "Rigel"), ("Rigel", "Saiph"), 
        ("Saiph", "Betelgeuse"), ("Betelgeuse", "Meissa"), ("Alnitak", "Alnilam"), 
        ("Alnilam", "Mintaka"), ("Mintaka", "Bellatrix"), ("Alnitak", "Saiph")
    ],
    "Ursa Major": [
        ("Dubhe", "Merak"), ("Merak", "Phecda"), ("Phecda", "Megrez"), 
        ("Megrez", "Dubhe"), ("Megrez", "Alioth"), ("Alioth", "Mizar"), ("Mizar", "Alkaid")
    ],
    "Cassiopeia": [
        ("Caph", "Schedar"), ("Schedar", "Navi"), ("Navi", "Ruchbah"), ("Ruchbah", "Segin")
    ],
    "Crux": [
        ("Acrux", "Mimosa"), ("Mimosa", "Gacrux"), ("Gacrux", "Imai"), ("Imai", "Acrux")
    ],
    "Scorpius": [
        ("Antares", "Acrab"), ("Acrab", "Dschubba"), ("Antares", "Paikauhale"), 
        ("Paikauhale", "Wei"), ("Wei", "Sargas"), ("Sargas", "Shaula"), ("Shaula", "Lesath")
    ],
    "Canis Major": [
        ("Sirius", "Mirzam"), ("Sirius", "Muliphein"), ("Sirius", "Wezen"), ("Wezen", "Adhara")
    ],
    "Gemini": [
        ("Pollux", "Castor"), ("Pollux", "Wasat"), ("Castor", "Mebsuta")
    ]
}

def add_constellations(fig, visible_stars_df):
    """
    Draws constellation lines by matching Star Names.
    This bypasses ID mismatches entirely.
    """
    # Create a lookup: Name -> {Alt, Az}
    # We use 'proper' column which contains names like "Betelgeuse"
    star_map = visible_stars_df.set_index('proper')[['altitude', 'azimuth']].to_dict('index')
    
    # Helper to clean up lookup (handle case sensitivity if needed)
    # For now, we assume standard capitalization from load_star_data
    
    for name, pairs in CONSTELLATIONS.items():
        x_lines, y_lines, z_lines = [], [], []
        has_lines = False
        
        for star1_name, star2_name in pairs:
            # Check if both stars are in the visible sky map
            if star1_name in star_map and star2_name in star_map:
                s1 = star_map[star1_name]
                s2 = star_map[star2_name]
                
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
                has_lines = True
        
        if has_lines:
            fig.add_trace(go.Scatter3d(
                x=x_lines, y=y_lines, z=z_lines,
                mode='lines',
                line=dict(color='rgba(0, 255, 255, 0.5)', width=5), # Cyan, Semi-transparent
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
        img = img.transpose(Image.FLIP_LEFT_RIGHT) # Keeps the fix for the logo
        
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
        print(f"Texture Error: {e}")
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

    # (E) Constellations (Name-Based)
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
