import os
import math
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STARS_CSV_PATH = os.path.join(BASE_DIR, "stars.csv.gz")
TERRAIN_PATH = os.path.join(BASE_DIR, "terrain.png")
DE421_PATH = os.path.join(BASE_DIR, "de421.bsp")

# --- 1. DATA LOADING (Cached & Cleaned) ---
@st.cache_data
def load_star_data():
    df = pd.read_csv(STARS_CSV_PATH, compression='gzip', usecols=['id', 'proper', 'ra', 'dec', 'mag'])
    df = df.dropna(subset=['id'])
    df['id'] = df['id'].astype(int)
    bright_stars = df[df['mag'] < 6.0].copy()
    bright_stars['proper'] = bright_stars['proper'].fillna('HIP ' + bright_stars['id'].astype(str))
    bright_stars['proper_clean'] = bright_stars['proper'].astype(str).str.upper().str.strip()
    return bright_stars

@st.cache_resource
def load_ephemeris():
    from skyfield.api import load
    if os.path.exists(DE421_PATH):
        return load(DE421_PATH)
    return load('de421.bsp')

# --- 2. CALCULATOR (Skyfield with Robust Spherical Trig Fallback) ---
def _trig_altaz(df: pd.DataFrame, lat: float, lon: float, dt_utc) -> pd.DataFrame:
    """Accurate vectorised Local Sidereal Time & equatorial to horizontal coordinate transformation."""
    # Julian Date
    year, month, day = dt_utc.year, dt_utc.month, dt_utc.day
    hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0 + dt_utc.microsecond / 3.6e9
    if month <= 2:
        year -= 1
        month += 12
    A = math.floor(year / 100)
    B = 2 - A + math.floor(A / 4)
    jd = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + B - 1524.5 + hour / 24.0
    d = jd - 2451545.0
    # Greenwich Mean Sidereal Time (degrees)
    gmst = (280.46061837 + 360.98564736629 * d) % 360.0
    # Local Sidereal Time
    lst_deg = (gmst + lon) % 360.0
    
    ra_deg = (df['ra'].to_numpy() * 15.0) % 360.0
    dec_rad = np.radians(df['dec'].to_numpy())
    lat_rad = np.radians(lat)
    
    ha_deg = (lst_deg - ra_deg) % 360.0
    ha_rad = np.radians(ha_deg)
    
    # Altitude
    sin_alt = np.sin(dec_rad) * np.sin(lat_rad) + np.cos(dec_rad) * np.cos(lat_rad) * np.cos(ha_rad)
    sin_alt = np.clip(sin_alt, -1.0, 1.0)
    alt_rad = np.arcsin(sin_alt)
    
    # Azimuth
    cos_az = (np.sin(dec_rad) - np.sin(alt_rad) * np.sin(lat_rad)) / (np.cos(alt_rad) * np.cos(lat_rad) + 1e-12)
    cos_az = np.clip(cos_az, -1.0, 1.0)
    sin_ha = np.sin(ha_rad)
    az_deg = np.degrees(np.arccos(cos_az))
    az_deg = np.where(sin_ha > 0, 360.0 - az_deg, az_deg)
    
    out_df = df.copy()
    out_df['altitude'] = np.degrees(alt_rad)
    out_df['azimuth'] = az_deg
    return out_df[out_df['altitude'] > 0]

def calculate_sky_positions(df, lat, lon, custom_time=None):
    try:
        from skyfield.api import Star, load, wgs84
        ts = load.timescale()
        t = ts.from_datetime(custom_time) if custom_time else ts.now()
        planets = load_ephemeris()
        earth = planets['earth']
        observer = earth + wgs84.latlon(lat, lon)
        stars = Star(ra_hours=df['ra'], dec_degrees=df['dec'])
        astrometric = observer.at(t).observe(stars)
        alt, az, _ = astrometric.apparent().altaz()
        df_copy = df.copy()
        df_copy['altitude'] = alt.degrees
        df_copy['azimuth'] = az.degrees
        return df_copy[df_copy['altitude'] > 0]
    except Exception:
        # Fallback to spherical astronomy
        return _trig_altaz(df, lat, lon, custom_time)

# --- 3. CONSTELLATION DATABASE (Refined Pairs) ---
CONSTELLATIONS = {
    "Orion (Hunter)": [
        ("BETELGEUSE", "MEISSA"), ("MEISSA", "BELLATRIX"),
        ("BETELGEUSE", "ALNITAK"), ("BELLATRIX", "MINTAKA"),
        ("ALNITAK", "ALNILAM"), ("ALNILAM", "MINTAKA"),
        ("ALNITAK", "SAIPH"), ("MINTAKA", "RIGEL"),
        ("RIGEL", "SAIPH")
    ],
    "Ursa Major (Big Dipper)": [
        ("DUBHE", "MERAK"), ("MERAK", "PHECDA"), ("PHECDA", "MEGREZ"),
        ("MEGREZ", "DUBHE"),
        ("MEGREZ", "ALIOTH"), ("ALIOTH", "MIZAR"), ("MIZAR", "ALKAID")
    ],
    "Cassiopeia (The Queen)": [
        ("CAPH", "SCHEDAR"), ("SCHEDAR", "NAVI"),
        ("NAVI", "RUCHBAH"), ("RUCHBAH", "SEGIN")
    ],
    "Leo (The Lion)": [
        ("REGULUS", "ALGIEBA"), ("ALGIEBA", "ADHAFERA"),
        ("ADHAFERA", "ALGENUBI"), ("ALGIEBA", "ZOSMA"),
        ("ZOSMA", "DENEBOLA"), ("ZOSMA", "CHERTAN"),
        ("CHERTAN", "REGULUS")
    ],
    "Crux (Southern Cross)": [
        ("ACRUX", "GACRUX"),
        ("MIMOSA", "IMAI")
    ],
    "Scorpius (Scorpion)": [
        ("ANTARES", "ALNIYAT"), ("ALNIYAT", "ACRAB"),
        ("ACRAB", "DSCHUBBA"),
        ("ANTARES", "WEI"), ("WEI", "SARGAS"),
        ("SARGAS", "SHAULA"), ("SHAULA", "LESATH")
    ],
    "Canis Major (Great Dog)": [
        ("SIRIUS", "MIRZAM"),
        ("SIRIUS", "MULIPHEIN"),
        ("SIRIUS", "WEZEN"),
        ("WEZEN", "ADHARA"),
        ("WEZEN", "ALUDRA")
    ],
    "Gemini (The Twins)": [
        ("POLLUX", "CASTOR"),
        ("POLLUX", "WASAT"), ("WASAT", "ALZIRR"),
        ("CASTOR", "MEBSUTA"), ("MEBSUTA", "TEJAT")
    ]
}

def add_constellations(fig, visible_stars_df):
    visible_stars_df = visible_stars_df.sort_values('mag', ascending=True)
    star_map = {}
    for _, row in visible_stars_df.iterrows():
        clean_name = row['proper_clean']
        if clean_name not in star_map:
            star_map[clean_name] = {'altitude': row['altitude'], 'azimuth': row['azimuth']}

    for name, pairs in CONSTELLATIONS.items():
        x_lines, y_lines, z_lines = [], [], []
        has_lines = False
        for star1, star2 in pairs:
            s1_data = star_map.get(star1)
            s2_data = star_map.get(star2)
            if not s1_data:
                for k in star_map:
                    if star1 in k:
                        s1_data = star_map[k]
                        break
            if not s2_data:
                for k in star_map:
                    if star2 in k:
                        s2_data = star_map[k]
                        break

            if s1_data and s2_data:
                for s in [s1_data, s2_data]:
                    alt, az = np.radians(s['altitude']), np.radians(s['azimuth'])
                    x_lines.append(100 * np.cos(alt) * np.sin(az))
                    y_lines.append(100 * np.cos(alt) * np.cos(az))
                    z_lines.append(100 * np.sin(alt))
                x_lines.append(None); y_lines.append(None); z_lines.append(None)
                has_lines = True
        
        if has_lines:
            fig.add_trace(go.Scatter3d(
                x=x_lines, y=y_lines, z=z_lines,
                mode='lines',
                line=dict(color='rgba(0, 240, 255, 0.65)', width=4),
                name=name,
                hoverinfo='name'
            ))
    return fig

# --- 4. IMAGE PROCESSOR (Cached) ---
@st.cache_data
def process_terrain_mesh(filename="terrain.png", resolution=250):
    xy = np.linspace(-100, 100, resolution)
    x_grid, y_grid = np.meshgrid(xy, xy)
    radius = np.sqrt(x_grid**2 + y_grid**2)
    mask = radius <= 100
    x_flat = x_grid[mask]
    y_flat = y_grid[mask]
    z_flat = np.full_like(x_flat, -2.0)
    
    file_path = os.path.join(BASE_DIR, filename)
    try:
        if not os.path.exists(file_path):
            return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(30,30,50)', dtype=object)
        img = Image.open(file_path).transpose(Image.FLIP_LEFT_RIGHT)
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
        img = img.crop((left, top, left + min_dim, top + min_dim))
        img = img.resize((resolution, resolution))
        img_array = np.array(img)
        R, G, B = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        color_grid = np.char.add(np.char.add(np.char.add('rgb(', R.astype(str)), ','), G.astype(str))
        color_grid = np.char.add(np.char.add(color_grid, ','), B.astype(str))
        color_grid = np.char.add(color_grid, ')')
        return x_flat, y_flat, z_flat, color_grid[mask]
    except Exception:
        return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(30,30,50)', dtype=object)

# --- 5. RAILING ---
def generate_railing():
    z_rail = np.linspace(-2, 5, 5)
    theta_rail = np.linspace(0, 2 * np.pi, 100)
    z_grid_rail, theta_grid_rail = np.meshgrid(z_rail, theta_rail)
    x_rail = 99 * np.cos(theta_grid_rail)
    y_rail = 99 * np.sin(theta_grid_rail)
    return x_rail, y_rail, z_grid_rail

# --- 6. CHART GENERATOR ---
def create_3d_sphere_chart(visible_stars, show_constellations=True):
    alt_rad = np.radians(visible_stars['altitude'])
    az_rad = np.radians(visible_stars['azimuth'])
    r_sphere = 100 
    x = r_sphere * np.cos(alt_rad) * np.sin(az_rad)
    y = r_sphere * np.cos(alt_rad) * np.cos(az_rad)
    z = r_sphere * np.sin(alt_rad)
    
    fig = go.Figure()

    # (A) Horizon Floor Mesh
    x_f, y_f, z_f, c_f = process_terrain_mesh("terrain.png", resolution=250)
    fig.add_trace(go.Mesh3d(
        x=x_f, y=y_f, z=z_f, vertexcolor=c_f, 
        name='Terrain Floor', hoverinfo='skip', opacity=1.0, delaunayaxis='z'
    ))

    # (B) Horizon Railing
    x_r, y_r, z_r = generate_railing()
    fig.add_trace(go.Surface(
        x=x_r, y=y_r, z=z_r, 
        colorscale=[[0, '#00d2ff'], [1, '#000510']], 
        showscale=False, opacity=0.45, name='Horizon Wall', hoverinfo='skip'
    ))

    # (C) Cardinal Compass
    fig.add_trace(go.Scatter3d(
        x=[0, 90, 0, -90], y=[90, 0, -90, 0], z=[-1.2]*4,
        mode='text', text=["<b>N</b>", "<b>E</b>", "<b>S</b>", "<b>W</b>"],
        textfont=dict(color=['#ff3355', '#4A90E2', '#4A90E2', '#4A90E2'], size=26, family="Arial Black"),
        hoverinfo='skip', name='Compass'
    ))

    # (D) Stars
    sizes = np.clip(5.5 - visible_stars['mag'], 1.5, 6.0)
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z, mode='markers',
        marker=dict(size=sizes, color='white', opacity=0.88, line=dict(width=0)),
        hovertext=visible_stars['proper'] + " (Mag " + visible_stars['mag'].round(1).astype(str) + ")", 
        name='Stars'
    ))

    # (E) Constellations
    if show_constellations:
        fig = add_constellations(fig, visible_stars)

    # (F) Observer
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[-1], mode='markers', 
        marker=dict(size=5, color='#00ff88'), name='Observer'
    ))

    fig.update_layout(
        template="plotly_dark",
        scene=dict(
            bgcolor='#020412',
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            dragmode="turntable",
            camera=dict(eye=dict(x=0.08, y=-0.08, z=0.08), up=dict(x=0, y=0, z=1))
        ),
        showlegend=False, 
        margin=dict(l=0, r=0, b=0, t=0), 
        height=540
    )
    return fig

# --- 7. 2D POLAR CHART ---
def create_star_chart(visible_stars):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=90 - visible_stars['altitude'], 
        theta=visible_stars['azimuth'], 
        mode='markers', 
        marker=dict(size=np.clip(11 - visible_stars['mag'] * 1.5, 1.0, 11), color='white', opacity=0.85), 
        hovertext=visible_stars['proper']
    ))
    fig.update_layout(
        template="plotly_dark", 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)', 
        polar=dict(
            bgcolor="#05081e", 
            radialaxis=dict(visible=False, range=[0, 90]), 
            angularaxis=dict(rotation=90, direction="clockwise", linecolor="rgba(74, 144, 226, 0.4)", gridcolor="rgba(74, 144, 226, 0.15)")
        ), 
        showlegend=False, 
        dragmode=False, 
        margin=dict(l=20, r=20, t=30, b=20), 
        height=500
    )
    for a, l in [(0, "N"), (90, "E"), (180, "S"), (270, "W")]: 
        fig.add_annotation(x=a, y=1.08, text=f"<b>{l}</b>", showarrow=False, font=dict(color="#4A90E2", size=14))
    return fig
