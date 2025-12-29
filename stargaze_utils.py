import pandas as pd
import numpy as np
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st
from PIL import Image
import os

# --- 1. CACHED DATA LOADING (The Speed Fix) ---
@st.cache_data
def load_star_data():
    """Loads star catalog once."""
    df = pd.read_csv("stars.csv.gz", compression='gzip', usecols=['id', 'proper', 'ra', 'dec', 'mag'])
    bright_stars = df[df['mag'] < 6.0].copy()
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
def create_3d_sphere_chart(visible_stars):
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
    return fig
