import pandas as pd
import numpy as np  # <-- This was missing!
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st

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

# In stargaze_utils.py

def generate_terrain():
    # 1. Create a grid (The ground)
    # We make a 50x50 grid covering an area of 100x100 units
    x = np.linspace(-50, 50, 50)
    y = np.linspace(-50, 50, 50)
    x_grid, y_grid = np.meshgrid(x, y)
    
    # 2. Generate Height (The Mountains)
    # We use a simple math formula to make "hills"
    # Sin waves + Random noise
    z_grid = np.sin(x_grid/10) * np.cos(y_grid/10) * 5  # Big rolling hills
    z_grid += np.random.normal(0, 0.5, z_grid.shape)    # Rough texture
    
    # Flatten the center (Where the user stands)
    # Any point within distance 10 of center gets flattened to 0
    distance_from_center = np.sqrt(x_grid**2 + y_grid**2)
    mask = distance_from_center < 15
    z_grid[mask] = z_grid[mask] * (distance_from_center[mask] / 15) # Smoothly flatten
    
    return x_grid, y_grid, z_grid

def create_3d_sphere_chart(visible_stars):
    # 1. CONVERT STARS TO 3D
    alt_rad = np.radians(visible_stars['altitude'])
    az_rad = np.radians(visible_stars['azimuth'])
    r_sphere = 100 # Star distance
    
    x = r_sphere * np.cos(alt_rad) * np.sin(az_rad)
    y = r_sphere * np.cos(alt_rad) * np.cos(az_rad)
    z = r_sphere * np.sin(alt_rad)
    
    fig = go.Figure()

    # ... inside create_3d_sphere_chart ...

    # 2. ADD THE TERRAIN (NEW!) 🏔️
    x_ground, y_ground, z_ground = generate_terrain()
    
    fig.add_trace(go.Surface(
        x=x_ground, y=y_ground, z=z_ground,
        colorscale='Earth', # Brown/Green colors
        showscale=False,
        opacity=0.9,
        name='Terrain',
        hoverinfo='skip'
    ))

    # 3. ADD STARS
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z,
        mode='markers',
        marker=dict(
            size=np.clip(5 - visible_stars['mag'], 1, 5),
            color='white',
            opacity=0.8,
            line=dict(width=0)
        ),
        hovertext=visible_stars['proper'],
        name='Stars'
    ))

    # 4. ADD OBSERVER (You)
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0],
        mode='markers',
        marker=dict(size=5, color='#00ff00'), # Green dot for user
        name='Observer'
    ))
    
    # 5. STYLE
    fig.update_layout(
        template="plotly_dark",
       # In stargaze_utils.py -> create_3d_sphere_chart

    # ... inside fig.update_layout( ...
        scene=dict(
            bgcolor='#000510',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            camera=dict(eye=dict(x=0.1, y=0.1, z=0.1))
        ),
        showlegend=False,  # <--- ADD THIS LINE to remove the sidebar key
        margin=dict(l=0, r=0, b=0, t=0),
        height=500
    )
    return fig
