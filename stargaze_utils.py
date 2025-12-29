import pandas as pd
import numpy as np
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st
from scipy.ndimage import gaussian_filter  # <--- NEW LIBRARY

# --- 1. DATA LOADING (Keep as is) ---
@st.cache_data
def load_star_data():
    df = pd.read_csv(
        "stars.csv.gz", 
        compression='gzip', 
        usecols=['id', 'proper', 'ra', 'dec', 'mag']
    )
    bright_stars = df[df['mag'] < 6.0].copy()
    bright_stars['proper'] = bright_stars['proper'].fillna('HIP ' + bright_stars['id'].astype(str))
    return bright_stars

# --- 2. SKY CALCULATOR (Keep as is) ---
def calculate_sky_positions(df, lat, lon, custom_time=None):
    ts = load.timescale()
    if custom_time:
        t = ts.from_datetime(custom_time)
    else:
        t = ts.now()

    planets = load('de421.bsp')
    earth = planets['earth']
    observer = earth + wgs84.latlon(lat, lon)
    stars = Star(ra_hours=df['ra'], dec_degrees=df['dec'])
    
    astrometric = observer.at(t).observe(stars)
    alt, az, distance = astrometric.apparent().altaz()
    
    df['altitude'] = alt.degrees
    df['azimuth'] = az.degrees
    return df[df['altitude'] > 0]

# --- 3. THE NEW TERRAIN GENERATOR (From Specialist) ---
def generate_smooth_terrain():
    # Grid Settings (We use 200x200 for nice detail)
    resolution = 200
    radius = 100 # Matches our star sphere size
    
    # 1. Create the Coordinate Grid
    xy = np.linspace(-radius, radius, resolution)
    x_grid, y_grid = np.meshgrid(xy, xy)
    
    # 2. Math Coordinates (for the Sine waves)
    # We map our -100 to 100 grid to a 0 to 4pi range for the math
    x_math = np.interp(x_grid, (x_grid.min(), x_grid.max()), (0, 4 * np.pi))
    y_math = np.interp(y_grid, (y_grid.min(), y_grid.max()), (0, 4 * np.pi))
    
    # 3. GENERATE HEIGHTS (The Specialist's "Octave" Logic)
    # Layer 1: Big Mountains (40% weight)
    z1 = 30 * np.sin(x_math / 2) * np.cos(y_math / 2)
    z1 = gaussian_filter(z1, sigma=8) # Smooth it out
    
    # Layer 2: Medium Hills (35% weight)
    z2 = 15 * np.sin(x_math) * np.cos(y_math)
    z2 = gaussian_filter(z2, sigma=4)
    
    # Layer 3: Small bumps (25% weight)
    z3 = 8 * np.sin(2*x_math) * np.cos(2*y_math)
    z3 = gaussian_filter(z3, sigma=2)
    
    # Combine layers
    z_grid = 0.4 * z1 + 0.35 * z2 + 0.25 * z3
    
    # 4. Normalize Heights (Keep mountains reasonable, e.g., max 30 units high)
    z_grid = ((z_grid - z_grid.min()) / (z_grid.max() - z_grid.min())) * 30
    z_grid -= 10 # Shift down so water is at 0
    
    # 5. THE CIRCULAR CUT (Our Stargaze Logic)
    # Remove corners so it fits inside the dome
    r = np.sqrt(x_grid**2 + y_grid**2)
    z_grid[r > 95] = np.nan
    
    return x_grid, y_grid, z_grid

# --- 4. COLOR GENERATOR (From Specialist) ---
def get_terrain_colors(z_grid):
    # Create an empty color array
    colors = np.zeros((*z_grid.shape, 3))
    
    # Define thresholds (Water, Grass, Rock, Snow)
    # We tweak these slightly for "Night Mode" (Darker colors)
    
    # Water (< 2 height): Dark Blue
    mask = z_grid < 2
    colors[mask] = [0.05, 0.1, 0.3] 
    
    # Grass (2 - 12 height): Dark Forest Green
    mask = (z_grid >= 2) & (z_grid < 12)
    colors[mask] = [0.1, 0.25, 0.1] 
    
    # Rock (12 - 20 height): Dark Grey/Brown
    mask = (z_grid >= 12) & (z_grid < 20)
    colors[mask] = [0.25, 0.2, 0.15]
    
    # Snow (> 20 height): Pale Blue-Grey (Not bright white)
    mask = z_grid >= 20
    colors[mask] = [0.6, 0.7, 0.8]
    
    return colors

# --- 5. THE 3D PLOTTER (Merged) ---
def create_3d_sphere_chart(visible_stars):
    fig = go.Figure()

    # A. ADD STARS
    alt_rad = np.radians(visible_stars['altitude'])
    az_rad = np.radians(visible_stars['azimuth'])
    r_sphere = 100 
    
    xs = r_sphere * np.cos(alt_rad) * np.sin(az_rad)
    ys = r_sphere * np.cos(alt_rad) * np.cos(az_rad)
    zs = r_sphere * np.sin(alt_rad)
    
    fig.add_trace(go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode='markers',
        marker=dict(size=np.clip(5 - visible_stars['mag'], 1, 5), color='white', opacity=0.8),
        hovertext=visible_stars['proper'],
        name='Stars'
    ))

    # B. ADD SMOOTH TERRAIN
    x_g, y_g, z_g = generate_smooth_terrain()
    color_map = get_terrain_colors(z_g)
    
    # Convert colors for Plotly
    surface_color = np.zeros((*color_map.shape[:2], 3), dtype=np.uint8)
    surface_color[:,:,0] = (color_map[:,:,0] * 255).astype(np.uint8)
    surface_color[:,:,1] = (color_map[:,:,1] * 255).astype(np.uint8)
    surface_color[:,:,2] = (color_map[:,:,2] * 255).astype(np.uint8)

    fig.add_trace(go.Surface(
        x=x_g, y=y_g, z=z_g,
        surfacecolor=surface_color,
        colorscale='Viridis', # Ignored because we use surfacecolor
        showscale=False,
        name='Terrain',
        hoverinfo='skip',
        lighting=dict(ambient=0.2, diffuse=0.7, roughness=0.8, specular=0.1)
    ))

    # C. LAYOUT
    fig.update_layout(
        template="plotly_dark",
        scene=dict(
            bgcolor='#000510',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            camera=dict(eye=dict(x=0.5, y=0.5, z=0.2)) # Nice low angle
        ),
        showlegend=False,
        margin=dict(l=0, r=0, b=0, t=0),
        height=500
    )
    return fig

# --- 6. 2D CHART (Keep as is) ---
def create_star_chart(visible_stars):
    # (Keep your existing 2D chart code here...)
    # If you need it again, I can paste it, but assume it's unchanged.
    pass
