import pandas as pd
import numpy as np  # <-- This was missing!
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st
from PIL import Image 
import os

# 1. The Loader (Emergency Version - No Download Needed)
@st.cache_data
def load_star_data():
    # We read the compressed file directly. 
    # Python unzips it in memory, so you don't have to extract it on Windows.
    df = pd.read_csv(
        "stars.csv.gz",  # The name of your uploaded file
        compression='gzip', 
        usecols=['id', 'proper', 'ra', 'dec', 'mag']
    )
    
    # Filter for bright stars only
    bright_stars = df[df['mag'] < 6.0].copy()
    bright_stars['proper'] = bright_stars['proper'].fillna('HIP ' + bright_stars['id'].astype(str))
    
    return bright_stars

# 2. The Calculator
# Update the definition to accept 'custom_time'
# In stargaze_utils.py

# 2. The Calculator (Updated to accept Time)
def calculate_sky_positions(df, lat, lon, custom_time=None):
    ts = load.timescale()
    
    # LOGIC: If 'app.py' sends a time, use it. Otherwise, use "now".
    if custom_time:
        t = ts.from_datetime(custom_time)
    else:
        t = ts.now()

    # Load Earth positions
    planets = load('de421.bsp')
    earth = planets['earth']
    
    observer = earth + wgs84.latlon(lat, lon)
    stars = Star(ra_hours=df['ra'], dec_degrees=df['dec'])
    
    astrometric = observer.at(t).observe(stars)
    alt, az, distance = astrometric.apparent().altaz()
    
    df['altitude'] = alt.degrees
    df['azimuth'] = az.degrees
    
    # Filter: Keep only stars above the horizon
    return df[df['altitude'] > 0]
# 3. The Plotter
def create_star_chart(visible_stars):
    fig = go.Figure()

    # 1. THE STARS (Improved Styling)
    fig.add_trace(go.Scatterpolar(
        r = 90 - visible_stars['altitude'],
        theta = visible_stars['azimuth'],
        mode = 'markers',
        marker = dict(
            # Dynamic size: Bright stars (Mag -1) -> Size 12, Dim stars (Mag 6) -> Size 0.5
            size = np.clip(12 - visible_stars['mag'] * 1.5, 0.5, 12),
            color = 'white',
            # Dynamic opacity: Bright stars are solid, dim stars are ghostly
            opacity = np.clip(1.2 - (visible_stars['mag'] / 6), 0.3, 1.0),
            line = dict(width=0) # No border around dots
        ),
        hovertext = visible_stars['proper'],
        hoverinfo = "text",
        name = "Stars"
    ))

    # 2. THE STELLARIUM UI (Removing the "Graph" look)
    fig.update_layout(
        template = "plotly_dark", # Dark theme base
        paper_bgcolor = 'black',  # Widget background
        plot_bgcolor = 'black',   # Chart background
        
        # Lock the view so it doesn't wiggle
        polar = dict(
            bgcolor = "#000510", # Very dark blue (Night Sky color)
            
            # Hide the radial grid (the circles)
            radialaxis = dict(
                visible = False, 
                range = [0, 90] # 0=Center(Zenith), 90=Edge(Horizon)
            ),
            
            # Customizing the Angular Axis (The Horizon Direction)
            angularaxis = dict(
                visible = True,
                showline = True,
                linecolor = "#444", # Subtle gray horizon line
                showgrid = False,   # Remove the "spider web" lines
                showticklabels = False, # Hide the "0, 45, 90" numbers
                direction = "clockwise",
                rotation = 90
            )
        ),
        
        # Disable zoom/pan tools (makes it feel like a static view)
        dragmode = False, 
        showlegend = False,
        
        # Clean margins
        margin = dict(l=20, r=20, t=20, b=20),
        height = 700
    )

    # 3. MANUAL COMPASS MARKERS (Replacing the ugly numbers)
    # We add N, E, S, W manually to look like a HUD
    directions = [
        (0, "N"), (45, "NE"), (90, "E"), (135, "SE"), 
        (180, "S"), (225, "SW"), (270, "W"), (315, "NW")
    ]
    
    for angle, label in directions:
        fig.add_annotation(
            x = angle, y = 1.1, # Position outside the circle
            text = f"<b>{label}</b>",
            showarrow = False,
            font = dict(size=14 if len(label)==1 else 10, color="#888")
            # Note: Annotations in polar plots are tricky in Plotly, 
            # often easier to just trust the user knows Up is North.
        )

    return fig
 # In stargaze_utils.py
# In stargaze_utils.py
# --- 4. IMAGE PROCESSOR (Fixed Path & Debugging) ---
def process_terrain_mesh(filename, resolution=300):
    """
    Generates a circular grid of points and matches them to image pixels.
    Includes robust path finding and error reporting.
    """
    # 1. Generate the Grid
    xy = np.linspace(-100, 100, resolution)
    x_grid, y_grid = np.meshgrid(xy, xy)
    
    # 2. Circle Mask
    radius = np.sqrt(x_grid**2 + y_grid**2)
    mask = radius <= 100
    
    x_flat = x_grid[mask]
    y_flat = y_grid[mask]
    z_flat = np.full_like(x_flat, -2) 
    
    # 3. Robust Path Construction
    # This finds the absolute path to the folder containing THIS script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, filename)

    try:
        # Check if file exists at the specific path
        if not os.path.exists(file_path):
            st.error(f"⚠️ Texture Missing! I looked here: {file_path}")
            # Return grey fallback so app doesn't crash
            return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(50,50,50)', dtype=object)
            
        img = Image.open(file_path)
        img = img.transpose(Image.FLIP_LEFT_RIGHT) # Fix Mirroring
        
        # Center Crop
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim)/2
        top = (height - min_dim)/2
        right = (width + min_dim)/2
        bottom = (height + min_dim)/2
        img = img.crop((left, top, right, bottom))
        
        # Resize & Color Process
        img = img.resize((resolution, resolution))
        img_array = np.array(img)
        R, G, B = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        
        # Create Color Strings
        color_grid = np.char.add(np.char.add(np.char.add('rgb(', R.astype(str)), ','), G.astype(str))
        color_grid = np.char.add(np.char.add(color_grid, ','), B.astype(str))
        color_grid = np.char.add(color_grid, ')')
        
        return x_flat, y_flat, z_flat, color_grid[mask]
        
    except Exception as e:
        st.error(f"⚠️ Texture Load Error: {e}")
        # Return grey fallback
        return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(50,50,50)', dtype=object)
# --- 5. RAILING GENERATOR ---
def generate_railing():
    # Vertical range for the wall
    z_rail = np.linspace(-2, 5, 5)
    # Full circle coordinates
    theta_rail = np.linspace(0, 2*np.pi, 100)
    
    # Create the mesh grid
    z_grid_rail, theta_grid_rail = np.meshgrid(z_rail, theta_rail)
    
    # Convert to Cartesian (at radius 99, just inside the stars)
    x_rail = 99 * np.cos(theta_grid_rail)
    y_rail = 99 * np.sin(theta_grid_rail)
    
    return x_rail, y_rail, z_grid_rail
# In stargaze_utils.py

# --- 6. 3D CHART GENERATOR (Updated Call) ---
def create_3d_sphere_chart(visible_stars):
    # --- A. STAR MATH ---
    alt_rad = np.radians(visible_stars['altitude'])
    az_rad = np.radians(visible_stars['azimuth'])
    r_sphere = 100 
    x = r_sphere * np.cos(alt_rad) * np.sin(az_rad)
    y = r_sphere * np.cos(alt_rad) * np.cos(az_rad)
    z = r_sphere * np.sin(alt_rad)
    
    fig = go.Figure()

    # --- B. ADD TEXTURED FLOOR ---
    # Call with HIGHER RESOLUTION (300)
    x_f, y_f, z_f, c_f = process_terrain_mesh("terrain.png", resolution=300)
    
    fig.add_trace(go.Mesh3d(
        x=x_f, y=y_f, z=z_f,
        vertexcolor=c_f, 
        name='Terrain Floor',
        hoverinfo='skip',
        opacity=1.0,
        delaunayaxis='z' 
    ))

    # --- C. RAILING ---
    x_r, y_r, z_r = generate_railing()
    fig.add_trace(go.Surface(
        x=x_r, y=y_r, z=z_r,
        colorscale=[[0, '#00d2ff'], [1, '#000510']], 
        showscale=False, opacity=0.6, 
        name='Horizon Wall', hoverinfo='skip'
    ))

    # --- D. COMPASS ---
    fig.add_trace(go.Scatter3d(
        x=[0, 90, 0, -90], y=[90, 0, -90, 0], z=[-1.5, -1.5, -1.5, -1.5],
        mode='text',
        text=["<b>N</b>", "<b>E</b>", "<b>S</b>", "<b>W</b>"],
        textfont=dict(color=['#ff3333', '#000510', '#000510', '#000510'], size=30, family="Arial Black"),
        hoverinfo='skip', name='Compass'
    ))

    # --- E. STARS ---
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z, mode='markers',
        marker=dict(size=np.clip(5 - visible_stars['mag'], 1, 5), color='white', opacity=0.8, line=dict(width=0)),
        hovertext=visible_stars['proper'], name='Stars'
    ))

    # --- F. OBSERVER ---
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[-1], mode='markers',
        marker=dict(size=4, color='#00ff00'), name='Observer'
    ))

    # --- G. LAYOUT ---
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
