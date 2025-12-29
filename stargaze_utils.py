import pandas as pd
import numpy as np  # <-- This was missing!
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st
from PIL import Image #

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
# In stargaze_utils.py
# --- 1. IMAGE LOADER (NEW!) ---
def load_terrain_texture(filename, resolution=200):
    """
    Loads 'terrain.png', crops it to a square, resizes it, 
    and converts it to a grid of color strings for Plotly.
    """
    try:
        # Load image
        img = Image.open(filename)
        
        # 1. CROP TO SQUARE (Center Crop)
        # We need a perfect square to map onto our circular coordinate system
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
        right = (width + min_dim) / 2
        bottom = (height + min_dim) / 2
        img = img.crop((left, top, right, bottom))
        
        # 2. RESIZE to match our grid resolution
        # Using simple resizing. For high res, increase 'resolution'
        img = img.resize((resolution, resolution))
        
        # 3. CONVERT TO PLOTLY COLORS
        # Convert image to numpy array (R, G, B)
        img_array = np.array(img)
        
        # Create an empty grid of strings
        color_grid = np.empty((resolution, resolution), dtype=object)
        
        # This loop creates "rgb(r,g,b)" strings for every pixel
        # (Vectorized for speed)
        R = img_array[:,:,0]
        G = img_array[:,:,1]
        B = img_array[:,:,2]
        
        # Combine into strings
        # Format: "rgb(120, 40, 255)"
        color_grid = np.char.add(np.char.add(np.char.add('rgb(', R.astype(str)), ','), G.astype(str))
        color_grid = np.char.add(np.char.add(color_grid, ','), B.astype(str))
        color_grid = np.char.add(color_grid, ')')
        
        return color_grid
        
    except Exception as e:
        # Fallback if image is missing: Return a Grey Grid
        print(f"Texture Error: {e}")
        return np.full((resolution, resolution), 'rgb(50,50,50)', dtype=object)

# --- 2. ARCHITECTURE GENERATOR (UPDATED FOR TEXTURES) ---
def generate_textured_deck(resolution=200):
    # We switch from Polar (Circles) to Cartesian (Squares) 
    # so the image pixels line up perfectly.
    
    # 1. Create a Square Grid (-100 to 100)
    xy = np.linspace(-100, 100, resolution)
    x_grid, y_grid = np.meshgrid(xy, xy)
    
    # 2. The Floor Height (Z)
    z_floor = np.zeros_like(x_grid) - 2
    
    # 3. Cut the Circle (The Cookie Cutter)
    # Any point further than 100 units from center is invisible
    radius = np.sqrt(x_grid**2 + y_grid**2)
    mask = radius > 100
    z_floor[mask] = np.nan # Hides the corners
    
    # 4. The Railing (Ring Wall) - Keeps using Polar for smooth curves
    z_rail = np.linspace(-2, 5, 5)
    theta_rail = np.linspace(0, 2*np.pi, 100)
    z_grid_rail, theta_grid_rail = np.meshgrid(z_rail, theta_rail)
    x_rail = 99 * np.cos(theta_grid_rail)
    y_rail = 99 * np.sin(theta_grid_rail)
    
    return (x_grid, y_grid, z_floor), (x_rail, y_rail, z_grid_rail)

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

def generate_observatory_deck():
    # PART A: THE FLOOR (Now extends to 100 radius to touch the horizon)
    # We use polar coordinates to make a perfect circle mesh
    r_floor = np.linspace(0, 100, 20)  # CHANGED: 20 -> 100 (Full Horizon)
    theta_floor = np.linspace(0, 2*np.pi, 60) # Increased resolution for smoothness
    r_grid, theta_grid = np.meshgrid(r_floor, theta_floor)
    
    x_floor = r_grid * np.cos(theta_grid)
    y_floor = r_grid * np.sin(theta_grid)
    
    # Place it at Z = -2 (just below eye level so you feel tall)
    z_floor = np.zeros_like(x_floor) - 2 

    # PART B: THE RAILING (The Rim at the Horizon)
    # A cylinder at radius 99 (just inside the 100 star sphere)
    z_rail = np.linspace(-2, 5, 5) # From floor (-2) up to a high wall (5)
    theta_rail = np.linspace(0, 2*np.pi, 100)
    z_grid_rail, theta_grid_rail = np.meshgrid(z_rail, theta_rail)
    
    x_rail = 99 * np.cos(theta_grid_rail) 
    y_rail = 99 * np.sin(theta_grid_rail)
    
    return (x_floor, y_floor, z_floor), (x_rail, y_rail, z_grid_rail)
    
# In stargaze_utils.py
# In stargaze_utils.py

# In stargaze_utils.py

def create_3d_sphere_chart(visible_stars):
    # --- 1. CONVERT STARS TO 3D ---
    alt_rad = np.radians(visible_stars['altitude'])
    az_rad = np.radians(visible_stars['azimuth'])
    r_sphere = 100 
    
    x = r_sphere * np.cos(alt_rad) * np.sin(az_rad)
    y = r_sphere * np.cos(alt_rad) * np.cos(az_rad)
    z = r_sphere * np.sin(alt_rad)
    
    fig = go.Figure()

    # --- 2. ADD THE TEXTURED DECK ---
    # Get Geometry and Texture
    (x_f, y_f, z_f), (x_r, y_r, z_r) = generate_textured_deck(resolution=200)
    texture_colors = load_terrain_texture("terrain.png", resolution=200)

    # Plot the Floor with the Image
    fig.add_trace(go.Surface(
        x=x_f, y=y_f, z=z_f,
        surfacecolor=texture_colors, # <--- THIS IS THE IMAGE
        showscale=False,
        name='Terrain Floor',
        hoverinfo='skip',
        # Lighting: High ambient so the image is visible, low diffuse so it's flat
        lighting=dict(ambient=0.8, diffuse=0.2, roughness=0.5, specular=0.0)
    ))

    # The Railing (Horizon Wall) - Kept same as before
    fig.add_trace(go.Surface(
        x=x_r, y=y_r, z=z_r,
        colorscale=[[0, '#00d2ff'], [1, '#000510']], 
        showscale=False, opacity=0.6, 
        name='Horizon Wall', hoverinfo='skip'
    ))

    # --- 3. CLEAN COMPASS (Initials Only) ---
    # Kept exactly as you had it
    fig.add_trace(go.Scatter3d(
        x=[0, 90, 0, -90],  # N, E, S, W
        y=[90, 0, -90, 0], 
        z=[-1.5, -1.5, -1.5, -1.5],
        mode='text',
        text=["<b>N</b>", "<b>E</b>", "<b>S</b>", "<b>W</b>"],
        textfont=dict(
            color=['#ff3333', '#000510', '#000510', '#000510'],
            size=30, 
            family="Arial Black"
        ),
        hoverinfo='skip',
        name='Compass'
    ))

    # --- 4. ADD STARS ---
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z,
        mode='markers',
        marker=dict(
            size=np.clip(5 - visible_stars['mag'], 1, 5),
            color='white', opacity=0.8, line=dict(width=0)
        ),
        hovertext=visible_stars['proper'],
        name='Stars'
    ))

    # --- 5. ADD OBSERVER ---
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[-1],
        mode='markers',
        marker=dict(size=4, color='#00ff00'),
        name='Observer'
    ))

    # --- 6. STYLE & CONTROLS ---
    fig.update_layout(
        template="plotly_dark",
        scene=dict(
            bgcolor='#000510',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            
            # REVERTED TO TURNTABLE (As requested)
            dragmode="turntable", 
            
            camera=dict(
                eye=dict(x=0.1, y=-0.1, z=0.1), 
                up=dict(x=0, y=0, z=1)
            )
        ),
        showlegend=False,
        margin=dict(l=0, r=0, b=0, t=0),
        height=500
    )
    
    return fig
