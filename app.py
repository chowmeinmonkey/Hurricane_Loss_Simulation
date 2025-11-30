"""
Florida Hurricane Risk Lab — Customizable Edition
Real-time hurricane loss simulation for Florida.
Adjust parameters → see impacts instantly.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
from folium.plugins import TimestampedGeoJson, HeatMap
from scipy.stats import poisson, norm

# ——————————————————————— Styling ———————————————————————
st.set_page_config(page_title="Hurricane Risk Lab", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    body {font-family: 'Inter', sans-serif;}
    .main {background: #0f172a; color: #e2e8f0;}
    h1 {color: #f472b6; font-weight: 700;}
    h2, h3 {color: #fbbf24;}

    .metric-card {
        background: rgba(251, 191, 36, 0.12);
        border: 1px solid rgba(251, 191, 36, 0.25);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        height: 140px;
    }
    .metric-label {font-size: 0.95rem; color: #94a3b8;}
    .metric-value {font-size: 1.8rem; font-weight: 700; color: #fbbf24;}

    .stButton>button {
        background: linear-gradient(90deg, #ec4899, #f59e0b);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        width: 100%;
        height: 50px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.05);
        border-radius: 12px 12px 0 0;
        padding: 12px 28px;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #ec4899, #f59e0b);
        color: white;
    }
    .block-container {padding-top: 2rem; max-width: 1400px;}
</style>
""", unsafe_allow_html=True)

# ——————————————————————— Portfolio Data ———————————————————————
@st.cache_data
def get_portfolio():
    return pd.DataFrame({
        "city": ["Miami", "Tampa", "Tallahassee", "Orlando", "Ft Lauderdale", "Jacksonville", "Key West", "Pensacola"],
        "insured_value": [500000, 750000, 1000000, 600000, 800000, 1200000, 450000, 900000],
        "construction_type": ["wood", "brick", "concrete", "wood", "brick", "concrete", "wood", "concrete"],
        "lat": [25.7617, 27.9478, 30.4383, 28.5383, 26.1224, 30.3322, 24.5551, 30.4213],
        "lon": [-80.1918, -82.4584, -84.2807, -81.3792, -80.1373, -81.6557, -81.7799, -87.2169]
    })

df = get_portfolio()

# ——————————————————————— Core Functions ———————————————————————
def vulnerability(wind_mph, construction="average"):
    base = max(0.0, min(1.0, wind_mph / 150))
    mult = {"wood": 1.50, "brick": 1.15, "concrete": 0.75}
    return min(1.0, base * mult.get(construction.lower(), 1.0))

def simulate_storm():
    center = (np.random.uniform(24.3, 31.0), np.random.uniform(-87.8, -79.8))
    wind = max(74, np.random.normal(110, 25))
    return wind, center

def calculate_loss(df, wind, center):
    radius_km = wind * 0.5
    total = 0
    impacts = []
    for _, row in df.iterrows():
        dist = ((row.lat - center[0])**2 + (row.lon - center[1])**2)**0.5 * 111
        if dist <= radius_km:
            dmg = vulnerability(wind, row.construction_type)
            loss = row.insured_value * dmg
            total += loss
            impacts.append((row.lat, row.lon, dmg))
        else:
            impacts.append((row.lat, row.lon, 0))
    return total, impacts

# ——————————————————————— Header ———————————————————————
st.markdown("""
<div style="text-align:center;padding:4rem 2rem;background:linear-gradient(135deg,rgba(236,72,153,0.15),rgba(245,158,11,0.15));border-radius:20px;border:1px solid rgba(236,72,153,0.3);margin-bottom:3rem;">
    <h1 style="font-size:4.5rem;margin:0;">Hurricane Risk Lab</h1>
    <p style="font-size:1.5rem;color:#cbd5e1;max-width:900px;margin:1.5rem auto;line-height:1.6;">
        Real-time catastrophe modeling for Florida using Monte-Carlo simulation.<br>
        Adjust parameters like hurricane frequency, wind speed, and climate impact to see how they affect insured losses across major cities.
    </p>
</div>
""", unsafe_allow_html=True)

# ——————————————————————— Sidebar Controls ———————————————————————
with st.sidebar:
    st.header("Simulation Parameters")
    
    hurricanes_per_year = st.slider("Average hurricanes per year", 0.1, 10.0, 0.56, 0.05)
    wind_mean = st.slider("Mean maximum wind speed (mph)", 80, 180, 110, 5)
    wind_std = st.slider("Wind speed standard deviation (mph)", 10, 50, 25, 5)
    vulnerability_threshold = st.slider("Vulnerability threshold (mph)", 100, 200, 150, 5)
    num_years = st.slider("Simulation years", 1000, 50000, 20000, 1000)
    
    st.markdown("---")
    st.subheader("Climate Scenario")
    climate = st.select_slider("Projected year", options=["Today", "2030", "2050", "2100"], value="Today")
    climate_factor = {"Today": 1.0, "2030": 1.12, "2050": 1.25, "2100": 1.45}[climate]
    st.markdown(f"**Intensity multiplier: ×{climate_factor:.2f}**")

# ——————————————————————— Live Risk Dashboard ———————————————————————
st.markdown("### Live Risk Dashboard")

@st.cache_data(ttl=30)
def quick_simulation():
    losses = []
    for _ in range(200):
        n = poisson.rvs(hurricanes_per_year * climate_factor)
        year_loss = 0
        for _ in range(n):
            wind = max(74, np.random.normal(wind_mean * climate_factor**0.4, wind_std))
            center = simulate_storm()[1]
            year_loss += calculate_loss(df, wind, center)[0]
        losses.append(year_loss)
    return np.array(losses)

losses = quick_simulation()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-label">Expected Annual Loss</div>
        <div class="metric-value">${np.mean(losses):,.0f}</div>
    </div>
    ''', unsafe_allow_html=True)
with col2:
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-label">99% VaR</div>
        <div class="metric-value">${np.quantile(losses, 0.99):,.0f}</div>
    </div>
    ''', unsafe_allow_html=True)
with col3:
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-label">Prob > $10M loss</div>
        <div class="metric-value">{(np.array(losses) > 10e6).mean():.1%}</div>
    </div>
    ''', unsafe_allow_html=True)
with col4:
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-label">Climate Multiplier</div>
        <div class="metric-value">×{climate_factor:.2f}</div>
    </div>
    ''', unsafe_allow_html=True)

# ——————————————————————— Tabs ———————————————————————
tab1, tab2, tab3 = st.tabs(["Loss Curve", "Animated Storm", "Damage Heatmap"])

with tab1:
    st.markdown("##### Loss Exceedance Curve")
    st.markdown("""
    This chart shows the probability of exceeding different loss levels in a given year.
    - The x-axis is the loss amount ($).
    - The y-axis is the chance of exceeding that loss (1% means a 1-in-100 year event).
    - Hover over points for details.
    """)
    if st.button("Run Simulation", type="primary"):
        with st.spinner(f"Simulating {num_years:,} years..."):
            full_losses = []
            total_storms = int(num_years * hurricanes_per_year * climate_factor * 1.5)
            winds = np.maximum(74, np.random.normal(wind_mean * climate_factor**0.4, wind_std, total_storms))
            centers_lat = np.random.uniform(24.3, 31.0, total_storms)
            centers_lon = np.random.uniform(-87.8, -79.8, total_storms)

            storm_idx = 0
            for _ in range(num_years):
                n = poisson.rvs(hurricanes_per_year * climate_factor)
                year_loss = 0
                for _ in range(n):
                    if storm_idx >= total_storms:
                        break
                    w = winds[storm_idx]
                    c = (centers_lat[storm_idx], centers_lon[storm_idx])
                    year_loss += calculate_loss(df, w, c)[0]
                    storm_idx += 1
                full_losses.append(year_loss)

            fig, ax = plt.subplots(figsize=(12,7))
            sorted_losses = sorted(full_losses, reverse=True)
            probs = np.linspace(1, 0, len(sorted_losses))
            ax.loglog(sorted_losses, probs, color="#f472b6", lw=3)
            ax.axvline(np.mean(full_losses), color='white', ls='--', lw=2, label=f'Expected Loss: ${np.mean(full_losses):,.0f}')
            ax.grid(True, which="both", ls="--", alpha=0.5)
            ax.set_title(f"Loss Exceedance Curve — {num_years:,} Years", fontsize=18, color="white")
            ax.set_xlabel("Annual Loss ($)", color="#e2e8f0")
            ax.set_ylabel("Exceedance Probability", color="#e2e8f0")
            ax.legend()
            st.pyplot(fig)

with tab2:
    st.markdown("##### Watch a Hurricane Make Landfall")
    if st.button("Generate Storm Animation"):
        wind, center = simulate_storm()
        track = []
        lat, lon = center
        for h in range(16):
            lat += np.random.normal(0.04, 0.015)
            lon -= 0.13
            wind_now = max(60, wind - h*5)
            track.append((lat, lon, wind_now))

        features = [
            {"type":"Feature","geometry":{"type":"Point","coordinates":[ln,lt]},
             "properties":{"time":f"2025-09-01T{h:02d}:00:00","popup":f"{w:.0f} mph"}}
            for h, (lt, ln, w) in enumerate(track)
        ]

        m = folium.Map(location=[27.5, -83], zoom_start=7, tiles="CartoDB dark_matter")
        TimestampedGeoJson({"type":"FeatureCollection","features":features},
                           period="PT1H", auto_play=True, loop=False).add_to(m)
        folium_static(m, width=900, height=550)

with tab3:
    st.markdown("##### Real-Time Damage Heatmap")
    if st.button("Show Current Storm Impact"):
        wind, center = simulate_storm()
        _, impacts = calculate_loss(df, wind, center)
        m = folium.Map(location=[27.8, -83], zoom_start=7, tiles="CartoDB positron")
        folium.Circle(location=center, radius=wind*1000, color="#ec4899", weight=3, fill_opacity=0.25).add_to(m)
        HeatMap([[lat, lon, dmg*120] for lat, lon, dmg in impacts], radius=25, blur=20).add_to(m)
        folium_static(m, width=900, height=550)

# ——————————————————————— Footer ———————————————————————
st.markdown("""
<div style="text-align:center;margin-top:6rem;padding:2rem;background:rgba(236,72,153,0.08);border-radius:16px;">
    <p style="color:#94a3b8;">Built with Streamlit • Open Source • Designed for risk professionals</p>
</div>
""", unsafe_allow_html=True)