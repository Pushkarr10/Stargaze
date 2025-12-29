import pandas as pd
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st

# 1. The Loader (Emergency Version - No Download Needed)
@st.cache_data
def load_star_data():
    # EMERGENCY FALLBACK: Manually create a tiny database of 10 bright stars
    data = {
        'id': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        'proper': ['Sun', 'Sirius', 'Canopus', 'Arcturus', 'Vega', 'Capella', 'Rigel', 'Procyon', 'Betelgeuse', 'Altair'],
        'ra': [0.0, 6.75, 6.40, 14.26, 18.62, 5.27, 5.24, 7.65, 5.92, 19.85],
        'dec': [0.0, -16.72, -52.70, 19.18, 38.78, 46.00, -8.20, 5.21, 7.41, 8.87],
        'mag': [-26.7, -1.46, -0.74, -0.05, 0.03, 0.08, 0.13, 0.34, 0.50, 0.77]
    }
    return pd.DataFrame(data)

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
