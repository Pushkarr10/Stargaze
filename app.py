import pandas as pd
import numpy as np
import plotly.graph_objects as go
from skyfield.api import Star, load, wgs84
import streamlit as st
from PIL import Image
import os

# --- 1. DATA LOADING (Cached & Cleaned) ---
@st.cache_data
def load_star_data():
    # Load raw data
    df = pd.read_csv("stars.csv.gz", compression='gzip', usecols=['id', 'proper', 'ra', 'dec', 'mag'])
    
    # Drop rows with no ID
    df = df.dropna(subset=['id'])
    df['id'] = df['id'].astype(int)
    
    # Filter for visible stars (Mag < 6.0)
    bright_stars = df[df['mag'] < 6.0].copy()
    
    # Fill missing names with HIP ID
    bright_stars['proper'] = bright_stars['proper'].fillna('HIP ' + bright_stars['id'].astype(str))
    
    # --- NORMALIZE NAMES ---
    # Convert to UPPERCASE and remove spaces for robust matching
    bright_stars['proper_clean'] = bright_stars['proper'].astype(str).str.upper().str.strip()
    
    return bright_stars

@st.cache_resource
def load_ephemeris():
    return load('de421.bsp')

# --- 2. CALCULATOR ---
def calculate_sky_positions(df, lat, lon, custom_time=None):
    ts = load.timescale()
    t = ts.from_datetime(custom_time) if custom_time else ts.now()
    planets = load_ephemeris()
    earth = planets['earth']
    observer = earth + wgs84.latlon(lat, lon)
    stars = Star(ra_hours=df['ra'], dec_degrees=df['dec'])
    astrometric = observer.at(t).observe(stars)
    alt, az, distance = astrometric.apparent().altaz()
    df['altitude'] = alt.degrees
    df['azimuth'] = az.degrees
    # Return only stars above horizon
    return df[df['altitude'] > 0]

# ==========================================
# --- 3. THE MODULAR ART SECTION ---
# ==========================================
# Edit THIS function to change constellation shapes.
# It's separate from the main chart logic.
# ==========================================
# --- 3. THE MODULAR ART SECTION (HIP IDs) ---
# ==========================================
def add_constellation_art(fig, visible_stars_df):
    """
    Draws detailed constellation art using HIP IDs.
    This ensures complex shapes (Shields, Tails) always connect correctly.
    """
    
    # --- 1. THE ART DATABASE (HIP IDs) ---
    # We use integers (HIP Numbers) because names are unreliable.
    
    # A. PRIMARY SHAPES (Thick Lines) - The main "Stick Figure"
    MAIN_BODY = {
        "Orion Body": [
            (27989, 26207), # Betelgeuse -> Meissa (Head)
            (26207, 25336), # Meissa -> Bellatrix (Shoulder)
            (27989, 26311), # Betelgeuse -> Alnitak (Belt)
            (25336, 25930), # Bellatrix -> Mintaka (Belt)
            (26311, 26727), (26727, 25930), # The Belt (Alnitak->Alnilam->Mintaka)
            (26311, 27366), # Alnitak -> Saiph (Leg)
            (25930, 24436), # Mintaka -> Rigel (Leg)
            (27366, 24436)  # Saiph -> Rigel (Feet Base)
        ],
        "Scorpius Body": [
            (80763, 78820), # Antares -> Acrab (Head)
            (78820, 78401), # Acrab -> Dschubba
            (78401, 78265), # Dschubba -> Pi Sco
            (80763, 81266), # Antares -> Tau Sco (Body Start)
            (81266, 82396), # Tau -> Epsilon (Wei)
            (82396, 82514), # Epsilon -> Mu
            (82514, 82729), # Mu -> Zeta
            (82729, 84143), # Zeta -> Eta
            (84143, 86228), # Eta -> Theta (Sargas)
            (86228, 87073), # Theta -> Iota
            (87073, 86670), # Iota -> Kappa
            (86670, 85927), # Kappa -> Lambda (Shaula - Stinger)
            (85927, 85696)  # Shaula -> Upsilon (Lesath - Stinger Tip)
        ],
        "Ursa Major": [
            (54061, 53910), (53910, 58001), (58001, 59774), # Cup
            (59774, 54061), # Cup Close
            (59774, 62956), (62956, 65378), (65378, 67301)  # Handle
        ],
        "Cassiopeia": [
            (11569, 94263), (94263, 4427), (4427, 2685), (2685, 8886)
        ],
        "Crux": [
            (60718, 59747), # Acrux -> Gacrux (Vertical)
            (62434, 58120)  # Mimosa -> Imai (Horizontal)
        ]
    }

    # B. SECONDARY ART (Thin/Faint Lines) - Shields, Clubs, Claws
    ART_DETAILS = {
        "Orion Shield": [
            (25336, 22449), # Bellatrix -> Pi1 (Shield Start)
            (22449, 22509), (22509, 22549), # Pi1->Pi2->Pi3
            (22549, 22797), (22797, 22957), # Pi3->Pi4->Pi5
            (22957, 23123)  # Pi5->Pi6
        ],
        "Orion Club": [
            (27989, 28814), # Betelgeuse -> Mu (Arm)
            (28814, 29038), (29038, 29426), # Mu->Nu->Xi (Club Up)
            (29426, 28716)  # Xi->Chi1 (Club Top)
        ],
        "Scorpius Claws": [
            (78820, 76333), # Acrab -> Nu Sco (Claw 1)
            (78401, 76041)  # Dschubba -> Rho Sco (Claw 2)
        ]
    }

    # --- 2. DRAWING LOGIC ---
    
    # Create a fast lookup: HIP_ID -> {Alt, Az}
    # We strictly use IDs now. No name guessing.
    star_map = {}
    for index, row in visible_stars_df.iterrows():
        try:
            # ID must be int
            star_map[int(row['id'])] = {'altitude': row['altitude'], 'azimuth': row['azimuth']}
        except: continue

    # Helper to draw a set of lines
    def draw_layer(dictionary, color, width, opacity):
        for name, pairs in dictionary.items():
            x_lines, y_lines, z_lines = [], [], []
            has_lines = False
            
            for hip1, hip2 in pairs:
                if hip1 in star_map and hip2 in star_map:
                    s1, s2 = star_map[hip1], star_map[hip2]
                    for s in [s1, s2]:
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
                    line=dict(color=color, width=width),
                    opacity=opacity,
                    name=name, hoverinfo='name'
                ))

    # Draw Main Body (Thick, Bright Cyan)
    draw_layer(MAIN_BODY, '#00FFFF', 5, 0.8)
    
    # Draw Art Details (Thin, Faint Blue)
    draw_layer(ART_DETAILS, '#89CFF0', 2, 0.5)

    return fig
# ==========================================
# --- END OF MODULAR ART SECTION ---
# ==========================================


# --- 4. IMAGE PROCESSOR (Cached) ---
@st.cache_data
def process_terrain_mesh(filename, resolution=300):
    xy = np.linspace(-100, 100, resolution)
    x_grid, y_grid = np.meshgrid(xy, xy)
    
    radius = np.sqrt(x_grid**2 + y_grid**2)
    mask = radius <= 100
    
    x_flat = x_grid[mask]
    y_flat = y_grid[mask]
    z_flat = np.full_like(x_flat, -2) 
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, filename)

    try:
        if not os.path.exists(file_path):
            return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(50,50,50)', dtype=object)
            
        img = Image.open(file_path)
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim)/2
        top = (height - min_dim)/2
        right = (width + min_dim)/2
        bottom = (height + min_dim)/2
        img = img.crop((left, top, right, bottom))
        
        img = img.resize((resolution, resolution))
        img_array = np.array(img)
        R, G, B = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        
        color_grid = np.char.add(np.char.add(np.char.add('rgb(', R.astype(str)), ','), G.astype(str))
        color_grid = np.char.add(np.char.add(color_grid, ','), B.astype(str))
        color_grid = np.char.add(color_grid, ')')
        
        return x_flat, y_flat, z_flat, color_grid[mask]
        
    except Exception as e:
        return x_flat, y_flat, z_flat, np.full_like(x_flat, 'rgb(50,50,50)', dtype=object)

# --- 5. RAILING ---
def generate_railing():
    z_rail = np.linspace(-2, 5, 5)
    theta_rail = np.linspace(0, 2*np.pi, 100)
    z_grid_rail, theta_grid_rail = np.meshgrid(z_rail, theta_rail)
    x_rail = 99 * np.cos(theta_grid_rail)
    y_rail = 99 * np.sin(theta_grid_rail)
    return x_rail, y_rail, z_grid_rail

# --- 6. MAIN CHART GENERATOR (Constant Part) ---
def create_3d_sphere_chart(visible_stars, show_constellations=False):
    alt_rad = np.radians(visible_stars['altitude'])
    az_rad = np.radians(visible_stars['azimuth'])
    r_sphere = 100 
    x = r_sphere * np.cos(alt_rad) * np.sin(az_rad)
    y = r_sphere * np.cos(alt_rad) * np.cos(az_rad)
    z = r_sphere * np.sin(alt_rad)
    
    fig = go.Figure()

    # (A) Floor
    x_f, y_f, z_f, c_f = process_terrain_mesh("terrain.png", resolution=300)
    fig.add_trace(go.Mesh3d(x=x_f, y=y_f, z=z_f, vertexcolor=c_f, name='Terrain Floor', hoverinfo='skip', opacity=1.0, delaunayaxis='z'))

    # (B) Railing
    x_r, y_r, z_r = generate_railing()
    fig.add_trace(go.Surface(x=x_r, y=y_r, z=z_r, colorscale=[[0, '#00d2ff'], [1, '#000510']], showscale=False, opacity=0.6, name='Horizon Wall', hoverinfo='skip'))

    # (C) Compass
    fig.add_trace(go.Scatter3d(
        x=[0, 90, 0, -90], y=[90, 0, -90, 0], z=[-1.5]*4,
        mode='text', text=["<b>N</b>", "<b>E</b>", "<b>S</b>", "<b>W</b>"],
        textfont=dict(color=['#ff3333', '#000510', '#000510', '#000510'], size=30, family="Arial Black"),
        hoverinfo='skip', name='Compass'
    ))

    # (D) Stars
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z, mode='markers',
        marker=dict(size=np.clip(5 - visible_stars['mag'], 1, 5), color='white', opacity=0.8, line=dict(width=0)),
        hovertext=visible_stars['proper'], name='Stars'
    ))

    # (E) The Modular Constellation Call
    if show_constellations:
        # This calls the separate art function we defined above
        fig = add_constellation_art(fig, visible_stars)

    # (F) Observer
    fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[-1], mode='markers', marker=dict(size=4, color='#00ff00'), name='Observer'))

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

# --- 7. 2D CHART ---
def create_star_chart(visible_stars):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r = 90 - visible_stars['altitude'], theta = visible_stars['azimuth'], mode = 'markers', marker = dict(size = np.clip(12 - visible_stars['mag'] * 1.5, 0.5, 12), color = 'white', opacity = 0.8), hovertext = visible_stars['proper']))
    fig.update_layout(template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black', polar=dict(bgcolor="#000510", radialaxis=dict(visible=False, range=[0, 90]), angularaxis=dict(rotation=90, direction="clockwise")), showlegend=False, dragmode=False, margin=dict(l=20, r=20, t=20, b=20), height=500)
    for a, l in [(0,"N"),(90,"E"),(180,"S"),(270,"W")]: fig.add_annotation(x=a, y=1.1, text=f"<b>{l}</b>", showarrow=False, font=dict(color="#888"))
    return fig
