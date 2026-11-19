# 🌌 Stargaze: The Celestial Observatory & Sky-Dex

A polished, production-ready **Python + Streamlit** astronomical application inspired by Stellarium and astrometry engines. It combines computer vision pattern recognition with interactive 3D/2D celestial simulation and collectible Sky-Dex gamification.

---

## 🌟 Key Features

### 1. 🔭 Deep Space Pattern Scanner
- **CLAHE Contrast Enhancement**: Normalizes dynamic range across astronomical night-sky captures.
- **Centroid Extraction & Filtering**: Connected components with tunable sensitivity and star area thresholds.
- **Delaunay Triangulation & Invariant Angle Barcodes**: Computes scale-, translation-, and rotation-invariant triangular signatures to match stars against the constellation database.
- **One-Click Synthetic Sky Generator**: Built-in generator to instantly simulate realistic night skies with exact geometric constellation stars and noise.

### 2. 🪐 Live Celestial Planetarium
- **3D Celestial Immersion**: Interactive 3D celestial dome with horizon terrain mesh (`terrain.png`), horizon wall railing, cardinal compass points, and 5,000+ stars scaled by astronomical magnitude.
- **2D Polar Star Chart**: Zenith-centered polar projection with compass markers.
- **Interactive World Map**: Folium dark map integration allowing observers to click anywhere on Earth to calibrate astronomical coordinates.
- **Temporal Time Machine**: Date picker and IST time slider with one-click "↺ Now" real-time synchronization.

### 3. ✨ The Cosmic Archive (Sky-Dex)
- **Gamified Sky-Dex**: Track unlocked constellations across rarity tiers (*Common*, *Uncommon*, *Rare*, *Legendary*).
- **Astronomical Lore**: Access mythology, viewing seasons, and brightest star coordinates.
- **Progress Export**: Download discovery logs in JSON format.

---

## 🚀 Quick Start

```bash
# Clone / navigate to repo
cd stargaze-constellation-dex

# Install dependencies
pip install -r requirements.txt

# Launch the Observatory
streamlit run app.py
```

---

## 📁 Repository Layout

```
stargaze-constellation-dex/
│   app.py                 # Celestial Observatory UI & Calibration Modes
│   stargaze_utils.py      # Ephemeris, coordinates & 3D/2D chart generator
│   stars.csv.gz           # Hipparcos star catalog dataset (5,020 bright stars)
│   terrain.png            # Horizon terrain texture for 3D immersion
│   dashboard_bg.png       # Cosmic space backdrop
│   de421.bsp              # Ephemeris data for high-precision astronomy
│   requirements.txt       # Dependencies
│   README.md              # Documentation
│
├───assets/                # High-resolution cosmic & neon wallpapers
├───core/
│       engine.py          # CV pipeline, Delaunay triangulation & barcode matcher
│       synthetic.py       # Synthetic night-sky generator
└───data/
        stars_db.json      # Constellation angle barcodes & collectible lore
```
