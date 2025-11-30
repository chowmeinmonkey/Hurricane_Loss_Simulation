"""
Florida Hurricane Risk Lab
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
from folium.plugins import TimestampedGeoJson, HeatMap
from folium import CircleMarker
from scipy.stats import poisson

# Initialize session state for tab control and storm data
if 'storm_launched' not in st.session_state:
    st.session_state.storm_launched = False
if 'storm_data' not in st.session_state:
    st.session_state.storm_data = None

# ——————————————————————— Styling ———————————————————————
st.set_page_config(page_title="Florida Hurricane Risk Lab", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    body {font-family: 'Inter', sans-serif;}
    .main {background: #0f172a; color: #e2e8f0;}
    h1, h2, h3 {color: #f472b6; font-weight: 600;}
    .metric-card {background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.25); border-radius: 16px; padding: 1.5rem; text-align: center; height: 140px;}
    .metric-label {font-size: 0.95rem; color: #94a3b8;}
    .metric-value {font-size: 1.8rem; font-weight: 700; color: #fbbf24;}
    .stButton>button {background: linear-gradient(90deg,#ec4899,#f59e0b); color: white; border: none; border-radius: 12px; height: 50px; font-weight: 600;}
    .explanation {background: rgba(236,72,153,0.08); padding: 1.2rem; border-radius: 12px; border-left: 4px solid #ec4899; margin: 1.5rem 0;}
</style>
""", unsafe_allow_html=True)

# ——————————————————————— Portfolio ———————————————————————
@st.cache_data
def get_portfolio():
    return pd.DataFrame({
        "city": ["Miami","Tampa","Tallahassee","Orlando","Ft Lauderdale","Jacksonville","Key West","Pensacola"],
        "insured_value": [500000,750000,1000000,600000,800000,1200000,450000,900000],
        "construction_type": ["wood","brick","concrete","wood","brick","concrete","wood","concrete"],
        "lat": [25.7617,27.9478,30.4383,28.5383,26.1224,30.3322,24.5551,30.4213],
        "lon": [-80.1918,-82.4584,-84.2807,-81.3792,-80.1373,-81.6557,-81.7799,-87.2169]
    })

df = get_portfolio()

# ——————————————————————— Model ———————————————————————
def vulnerability(wind_mph, construction):
    base = max(0.0, min(1.0, wind_mph / 150))
    mult = {"wood":1.5, "brick":1.15, "concrete":0.75}
    return min(1.0, base * mult.get(construction.lower(), 1.0))

def simulate_storm():
    # FIX: Corrected unmatched parenthesis and ensured clean spaces
    center = (np.random.uniform(24.3, 31.0), np.random.uniform(-87.8, -79.8))
    wind = max(74, np.random.normal(110, 25))
    return wind, center

def calculate_loss(df, wind, center):
    radius_km = wind * 0.5
    total = 0
    impacts = []
    for _, row in df.iterrows():
        # Approximate distance calculation
        dist = ((row.lat-center[0])**2 + (row.lon-center[1])**2)**0.5 * 111
        if dist <= radius_km:
            dmg = vulnerability(wind, row.construction_type)
            total += row.insured_value * dmg
            impacts.append((row.lat, row.lon, dmg))
        else:
            impacts.append((row.lat, row.lon, 0))
    return total, impacts

# ——————————————————————— Header ———————————————————————
st.markdown("""
<div style="text-align:center;padding:4rem 2rem;background:linear-gradient(135deg,rgba(236,72,153,0.15),rgba(245,158,11,0.15));border-radius:20px;margin-bottom:3rem;">
    <h1>Florida Hurricane Risk Lab</h1>
    <p style="font-size:1.5rem;color:#cbd5e1;max-width:900px;margin:1.5rem auto;">
        Interactive Monte-Carlo simulation of hurricane risk and insured losses in Florida.
    </p>
</div>
""", unsafe_allow_html=True)

# ——————————————————————— Sidebar ———————————————————————
with st.sidebar:
    st.header("Parameters")
    # Added keys to track parameter changes
    hurricanes_per_year = st.slider("Hurricanes per year", 0.1, 10.0, 0.56, 0.05, key="hpy")
    wind_mean = st.slider("Mean max wind (mph)", 80, 180, 110, 5, key="wm")
    wind_std = st.slider("Wind std dev (mph)", 10, 50, 25, 5, key="ws")
    sim_years = st.slider("Simulation years", 5_000, 50_000, 20_000, 5_000, key="sy")

    st.markdown("---")
    st.subheader("Climate Scenario")
    climate = st.select_slider("Year", options=["Today","2030","2050","2100"], value="Today", key="cl")
    climate_factor = {"Today":1.0,"2030":1.12,"2050":1.25,"2100":1.45}[climate]
    st.write(f"Intensity ×{climate_factor:.2f}")

# Reset storm animation state if parameters change
if any(st.session_state[k] != st.session_state.get(f'prev_{k}', st.session_state[k]) for k in ["hpy", "wm", "ws", "sy", "cl"]):
    st.session_state.storm_launched = False
for k in ["hpy", "wm", "ws", "sy", "cl"]:
    st.session_state[f'prev_{k}'] = st.session_state[k]

# ——————————————————————— Dashboard ———————————————————————
st.markdown("### Risk Summary")
@st.cache_data(ttl=30)
def quick_sim(hpy, wm, ws, cf): 
    losses = []
    for _ in range(300):
        n = poisson.rvs(hpy * cf)
        year_loss = 0
        for _ in range(n):
            w = max(74, np.random.normal(wm * cf**0.4, ws))
            c = simulate_storm()[1]
            year_loss += calculate_loss(df, w, c)[0]
        losses.append(year_loss)
    return np.array(losses)

losses = quick_sim(hurricanes_per_year, wind_mean, wind_std, climate_factor)
c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(f'<div class="metric-card"><div class="metric-label">Expected Annual Loss</div><div class="metric-value">${losses.mean():,.0f}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card"><div class="metric-label">99% VaR</div><div class="metric-value">${np.quantile(losses,0.99):,.0f}</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-card"><div class="metric-label">P(Loss > $10M)</div><div class="metric-value">{(losses>10e6).mean():.1%}</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="metric-card"><div class="metric-label">Climate Multiplier</div><div class="metric-value">×{climate_factor:.2f}</div></div>', unsafe_allow_html=True)

# ——————————————————————— Tabs ———————————————————————
tab1, tab2, tab3 = st.tabs(["Loss Exceedance Curve", "Storm Animation", "Single Storm"])

with tab1:
    st.markdown("#### Loss Exceedance Curve")
    st.markdown("""
    <div class="explanation">
    <strong>What the red line means:</strong><br>
    Each point on the <span style="color:#ef4444;font-weight:700;">red line</span> tells you:<br>
    “There is an X% chance (or 1-in-1/X years) that annual insured losses will exceed $Y”.<br><br>
    Example: If the curve passes through (10 000 000, 0.01) &rarr; there is a <strong>1-in-100-year chance</strong> of losses > $10 million.<br>
    The yellow dashed line is the Expected Annual Loss (average over all simulated years).
    </div>
    """, unsafe_allow_html=True)

    if st.button("Run Full Simulation", type="primary"):
        progress = st.progress(0)
        status = st.empty()

        total_storms = int(sim_years * hurricanes_per_year * climate_factor * 1.5)
        winds = np.maximum(74, np.random.normal(wind_mean * climate_factor**0.4, wind_std, total_storms))
        lats = np.random.uniform(24.3, 31.0, total_storms)
        lons = np.random.uniform(-87.8, -79.8, total_storms)

        yearly = []
        idx = 0
        for y in range(sim_years):
            n = poisson.rvs(hurricanes_per_year * climate_factor)
            loss = 0
            for _ in range(n):
                if idx >= total_storms: break
                loss += calculate_loss(df, winds[idx], (lats[idx], lons[idx]))[0]
                idx += 1
            yearly.append(loss)
            progress.progress((y+1)/sim_years)
            status.text(f"Year {y+1:,} of {sim_years:,}")

        progress.empty()
        status.empty()

        fig, ax = plt.subplots(figsize=(12,7))
        sorted_l = sorted(yearly, reverse=True)
        ax.loglog(sorted_l, np.linspace(1,0,len(sorted_l)), color="#ef4444", lw=3.5, label="Exceedance probability")
        ax.axvline(np.mean(yearly), color="#fbbf24", ls="--", lw=2, label=f'Expected Annual Loss: ${np.mean(yearly):,.0f}')
        ax.grid(True, which="both", ls="--", alpha=0.5)
        ax.set_title(f"Loss Exceedance Curve — {sim_years:,} Years", color="white", fontsize=18)
        ax.set_xlabel("Annual Insured Loss ($)", color="#e2e8f0")
        ax.set_ylabel("Exceedance Probability", color="#e2e8f0")
        ax.legend()
        st.pyplot(fig)

with tab2:
    st.markdown("#### Hurricane Landfall Animation")
    st.markdown("""
    <div class="explanation">
    &bullet; <strong>Red dot</strong> = hurricane eye<br>
    &bullet; <strong>Translucent red circle</strong> = full radius of hurricane-force winds (∼ wind speed &times; 0.5 km)<br>
    &bullet; Damage occurs anywhere inside this circle &mdash; that’s why even storms that “miss” Florida can still cause losses.
    </div>
    """, unsafe_allow_html=True)

    # FIX 1: Use session_state to store storm data and control the rendering
    if st.button("Launch Storm", key="launch_storm_button_2"):
        st.session_state.storm_data = simulate_storm()
        st.session_state.storm_launched = True

    if st.session_state.storm_launched and st.session_state.storm_data:
        wind, center = st.session_state.storm_data
        features = []
        lat, lon = center
        
        base_time = pd.to_datetime('2025-09-01T00:00:00')

        for h in range(16):
            lat += np.random.normal(0.04, 0.015)
            lon -= 0.13
            wind_now = max(60, wind - h*5)
            
            current_time = base_time + pd.Timedelta(hours=h)
            time_str = current_time.isoformat()

            # FIX 2: Correct GeoJSON structure for the moving radius circle
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "time": time_str,
                    "popup": f"Radius – {wind_now:.0f} mph",
                    # Radius style, scaled for map visibility
                    "style": {
                        "radius": wind_now * 0.5 * 0.5,
                        "fillColor": "#ef4444",
                        "color": "#ef4444",
                        "weight": 2,
                        "opacity": 0.8,
                        "fillOpacity": 0.15
                    }
                }
            })

            # The eye marker
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "time": time_str,
                    "popup": f"Eye – {wind_now:.0f} mph",
                    "icon": "circle",
                    "iconstyle": {"color": "#ef4444", "fillColor": "#ef4444", "weight": 4, "radius": 10}
                }
            })

        m = folium.Map(location=[27.5, -83], zoom_start=7, tiles="CartoDB dark_matter")
        TimestampedGeoJson(
            {"type": "FeatureCollection", "features": features},
            period="PT1H", 
            auto_play=True, 
            loop=False, 
            add_last_point=True,
            duration='PT16H', # Set duration for smoother slider playback
            transition_time=500
        ).add_to(m)
        folium_static(m, width=900, height=550)

with tab3:
    st.markdown("#### Single Storm Damage Map")
    st.markdown("""
    <div class="explanation">
    &bullet; Red circle = full hurricane-force wind field<br>
    &bullet; Heat = damage &times; insured value at each city
    </div>
    """, unsafe_allow_html=True)

    if st.button("Generate Storm", key="generate_single_storm"):
        wind, center = simulate_storm()
        _, impacts = calculate_loss(df, wind, center)

        m = folium.Map(location=[27.8, -83], zoom_start=7, tiles="CartoDB positron")
        # Full radius
        CircleMarker(
            location=center,
            radius=wind*900,
            color="#ef4444",
            weight=3,
            fillOpacity=0.18,
            popup=f"{wind:.0f} mph hurricane"
        ).add_to(m)
        # Eye
        CircleMarker(location=center, radius=15, color="#ef4444", fillColor="#ef4444").add_to(m)
        HeatMap([[lat,lon,dmg*150] for lat,lon,dmg in impacts], radius=25, blur=20).add_to(m)
        folium_static(m, width=900, height=550)

# ——————————————————————— Footer ———————————————————————
with st.expander("Technical Methodology"):
    st.markdown("""
    - Frequency: Poisson($\lambda \\times$ climate factor)  
    - Intensity: Normal($\mu \\times$ climate$^{0.4}$, $\\sigma$), $\\geq 74$ mph  
    - Footprint: Circular radius $\\approx$ wind $\\times 0.5$ km  
    - Vulnerability: Damage $=$ min$(1, \\text{wind}/150 \\times \\text{building factor})$
    """)

st.markdown("<p style='text-align:center;color:#64748b;margin-top:4rem;'>Michael A. Campion • 2025</p>", unsafe_allow_html=True)