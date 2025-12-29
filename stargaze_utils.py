import pandas as pd
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st # Only needed if you use @st.cache_data
@st.cache_data
# 1.The loader
def load_star_data():
    # UPDATED URL: We use the .gz version which is smaller and correct
    url = "https://raw.githubusercontent.com/astronexus/HYG-Database/master/hygdata_v3.csv.gz"
    
    # We add compression='gzip' to tell Pandas to unzip it
    df = pd.read_csv(url, compression='gzip', usecols=['id', 'proper', 'ra', 'dec', 'mag'])
    
    # The rest remains the same...
    bright_stars = df[df['mag'] < 6.0].copy()
    bright_stars['proper'] = bright_stars['proper'].fillna('HIP ' + bright_stars['id'].astype(str))
    return bright_stars

# 2. The Calculator
def calculate_sky_positions(df, lat, lon):
    ts = load.timescale()
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

# 3. The Plotter (Returns a 'fig' object, doesn't draw it yet)
def create_star_chart(visible_stars):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r = 90 - visible_stars['altitude'],
        theta = visible_stars['azimuth'],
        mode = 'markers',
        marker = dict(
            size = 8 - visible_stars['mag'],
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
