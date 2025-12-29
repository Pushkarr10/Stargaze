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

def generate_terrain():
    # 1. High Resolution Grid for jagged details
    xy_range = np.linspace(-100, 100, 150)
    x_grid, y_grid = np.meshgrid(xy_range, xy_range)
    
    # Calculate distance from center for every point
    r = np.sqrt(x_grid**2 + y_grid**2)
    
    # 2. Base Layer: The "Valley Floor"
    # FIX: We use 'x_grid.shape' here because z_grid doesn't exist yet
    z_grid = np.random.normal(0, 0.4, x_grid.shape)
    
    # Add slight rolling bumps
    z_grid += np.sin(x_grid/7) * np.cos(y_grid/7) * 1.5

    # 3. The "Ring Mountains" (The Walls)
    # We define a threshold. Past radius 40, mountains start rising.
    valley_radius = 40
    mountain_mask = r > valley_radius
    
    # The math: (distance past valley edge)^Power
    steepness_factor = 2.2 
    height_multiplier = 0.05
    
    # Apply the rise only to the mountain area
    z_grid[mountain_mask] += (r[mountain_mask] - valley_radius)**steepness_factor * height_multiplier
    
    # 4. Add "Craggy/Icy" details on top of the mountains
    # Higher frequency noise that gets stronger further out
    jaggedness = np.sin(x_grid/2) * np.sin(y_grid/3) * (r/100)**2 * 5
    z_grid += jaggedness

    # 5. The Horizon Cut (Circular Limit)
    # Cut sharply at radius 98 so it fits inside the 100-radius star sphere
    z_grid[r > 98] = np.nan
    
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

   # ... inside create_3d_sphere_chart ...

   # ... inside create_3d_sphere_chart ...

    # 2. ADD THE "STARLIT VALLEY" TERRAIN 🏔️🌑
    x_ground, y_ground, z_ground = generate_terrain()
    
    fig.add_trace(go.Surface(
        x=x_ground, y=y_ground, z=z_ground,
        
        # CUSTOM COLORSCALE: Night Valley -> Icy Peaks
        colorscale=[
            # Bottom of the valley (Deep Night Grass Green)
            [0.0, '#030f03'], 
            # Slightly higher grassy slopes (Desaturated dark green)
            [0.2, '#0d2112'], 
            # Transition zone where snow meets rock (Dark grey-blue)
            [0.5, '#1c2b36'],
            # Lower ice caps (Cold, dark blue-grey)
            [0.8, '#3e4f5c'],
            # Highest peaks catching faint starlight (Desaturated icy blue-white)
            # IMPORTANT: Don't make this bright white, it must look lit by stars.
            [1.0, '#6b7f8c']  
        ],
        
        # Lighting effects for icy realism
        lighting=dict(
            ambient=0.15, # Overall dim starlight
            diffuse=0.8,  # Rough texture for rock/grass
            fresnel=0.4,  # Adds a slight "rim lighting" effect to edges (good for ice)
            specular=0.3, # Slight shiny highlights on the ice peaks
            roughness=0.7 # Fairly rough surface
        ),
        
        showscale=False,
        opacity=1.0,
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
