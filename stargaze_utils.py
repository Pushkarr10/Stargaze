import pandas as pd
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
def calculate_sky_positions(df, lat, lon):
    ts = load.timescale()
    t = ts.now()
    
    # Load Earth positions (Skyfield will download a small file 'de421.bsp' once)
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
