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
def create_star_chart(visible_stars):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r = 90 - visible_stars['altitude'],
        theta = visible_stars['azimuth'],
        mode = 'markers',
        marker = dict(
            size = 10,  # Fixed size for this test
            color = 'white',
            opacity = 0.8
        ),
        hovertext = visible_stars['proper']
    ))
    
    fig.update_layout(
        polar = dict(
            bgcolor = "black",
            radialaxis = dict(visible = False, range = [0, 90]),
            angularaxis = dict(direction = "clockwise", rotation = 90, color = "white")
        ),
        paper_bgcolor = "black",
        height = 750,
        margin = dict(l=20, r=20, t=20, b=20)
    )
    return fig
