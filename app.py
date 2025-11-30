"""
Florida Hurricane Risk Lab
Interactive Monte-Carlo catastrophe model for Florida hurricane losses.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static        # ← fixed
from folium.plugins import TimestampedGeoJson, HeatMap
from folium import CircleMarker
from scipy.stats import poisson

# ——————————————————————— Styling ———————————————————————
st.set_page_config(page_title="Florida Hurricane Risk Lab", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    body {font-family: 'Inter', sans-serif;}
    .main {background: #0f172a; color: #e2e8f0;}
    h1, h2, h3 {color: #f472b6; font-weight: 600;}
    .metric-card {
        background: rgba(251, 191, 36, 0.12);
        border: 1px solid rgba(251, 191, 36, 0.25);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        height: 140px;
    }
    .metric-label {font-size: 0.95rem; color: #94a3b8;}
    .metric-value {font-size: 1.8rem; font-weight: 700; color: #fbbf24;}
    .stButton>button {background: linear-gradient(90deg, #ec4899, #f59e0b); color: white; border: none; border-radius: 12px; height: 50px; font-weight: 600;}
    .explanation {background: rgba(236,72,153,0.08); padding: 1.2rem; border-radius: 12px; border-left: 4px solid #ec4899; margin: 1.5rem 0;}
    .block-container {padding-top: 2rem; max-width: 1400px;}
</style>
""", unsafe_allow_html=True)

# ——————————————————————— Data ———————————————————————
@st.cache_data
def get_portfolio():
    return pd.DataFrame({
        "city": ["Miami", "Tampa", "Tallahassee", "Orlando", "Ft Lauderdale", "Jacksonville", "Key West", "Pensacola"],
        "insured_value": [500000, 750000, 1000000, 600000, 800000, 1200000, 450000, 900000],
        "construction_type": ["wood", "brick", "concrete", "wood", "brick", "concrete", "wood", "concrete"],
        "lat": [25.7617, 27.9478, 30.4383, 28.5383, 26.1224, 30: 30.3322, 24.5551, 30.4213],
        "lon": [-80.1918, -82.4584, -84.2807, -81.3792, -80.1373, -81.6557, -81.7799, -87.2169]
    })

df = get_portfolio()

# ——————————————————————— Model ———————————————————————
def vulnerability(wind_mph, construction):
    base = max(0.0, min(1.0, wind_mph / 150))
    mult = {"wood": 1.5, "brick": 1.15, "concrete": 0.75}
    return min(1.0, base * mult.get(construction.lower(), 1.0))

def simulate_storm():
    center = (np.random.uniform(24.3, 31.0), np.random.uniform(-87.8, -79.8))
    wind = max(74, np.random.normal(110, 25))
    return wind, center

def calculate_loss(df, wind, center):
    radius_km = wind * 0.5
    total_loss = 0
    impacts = []
    for _, row in df.iterrows():
        dist_km = ((row.lat - center[0])**2 + (row.lon - center[1])**2)**0.5 * 111
        if dist_km <= radius_km:
            dmg = vulnerability(wind, row.construction_type)
            total_loss += row.insured_value * dmg
            impacts.append((row.lat, row.lon, dmg))
        else:
            impacts.append((row.lat, row.lon, 0))
    return total_loss, impacts

# ——————————————————————— Header ———————————————————————
st.markdown("""
<div style="text-align:center; padding:4rem 2rem; background:linear-gradient(135deg,rgba(236,72,153,0.15),rgba(245,158,11,0.15)); border-radius:20px; margin-bottom:3rem;">
    <h1>Florida Hurricane Risk Lab</h1>
    <p style="font-size:1.5rem; color:#cbd5e1; max-width:900px; margin:1.5rem auto;">
        Monte-Carlo simulation of hurricane frequency, intensity, and insured losses across major Florida cities.
    </p>
</div>
""", unsafe_allow_html=True)

# ——————————————————————— Controls ———————————————————————
with st.sidebar:
    st.header("Parameters")
    hurricanes_per_year = st.slider("Hurricanes per year", 0.1, 10.0, 0.56, 0.05)
    wind_mean = st.slider("Mean wind speed (mph)", 80, 180, 110, 5)
    wind_std = st.slider("Wind speed std dev (mph)", 10, 50, 25, 5)
    sim_years = st.slider("Simulation years", 5_000, 50_000, 20_000, 5_000)

    st.markdown("---")
    st.subheader("Climate Scenario")
    climate = st.select_slider("Year", options=["Today", "2030", "2050", "2100"], value="Today")
    climate_factor = {"Today": 1.0, "2030": 1.12, "2050": 1.25, "2100": 1.45}[climate]
    st.write(f"Intensity ×{climate_factor:.2f}")

# ——————————————————————— Live Dashboard ———————————————————————
st.markdown("### Risk Summary")

@st.cache_data(ttl=30)
def quick_simulation():
    losses = []
    for _ in range(300):
        n = poisson.rvs(hurricanes_per_year * climate_factor)
        year_loss = 0
        for _ in range(n):
            w = max(74, np.random.normal(wind_mean * climate_factor**0.4, wind_std))
            c = simulate_storm()[1]
            year_loss += calculate_loss(df, w, c)[0]
        losses.append(year_loss)
    return np.array(losses)

losses = quick_simulation()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Expected Annual Loss</div><div class="metric-value">${losses.mean():,.0f}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">99% VaR</div><div class="metric-value">${np.quantile(losses,0.99):,.0f}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">P(Loss > $10M)</div><div class="metric-value">{(losses>10e6).mean():.1%}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Climate Multiplier</div><div class="metric-value">×{climate_factor:.2f}</div></div>', unsafe_allow_html=True)

# ——————————————————————— Tabs ———————————————————————
tab1, tab2, tab3 = st.tabs(["Loss Exceedance Curve", "Storm Animation", "Damage Map"])

with tab1:
    st.markdown("#### Loss Exceedance Curve")
    st.markdown("""
    <div class="explanation">
    <strong>Interpretation:</strong><br>
    • X-axis: Annual insured loss ($)<br>
    • Y-axis: Probability of exceeding that loss in any given year<br>
    • Example: a point at (10M, 0.01) means there is a <strong>1% chance</strong> (i.e. a <strong>1-in-100-year event</strong>) of losses exceeding $10 million in a year.<br>
    • The curve is built from thousands of simulated years.
    </div>
    """, unsafe_allow_html=True)

    if st.button("Run Simulation", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        total_storms = int(sim_years * hurricanes_per_year * climate_factor * 1.5)
        winds = np.maximum(74, np.random.normal(wind_mean * climate_factor**0.4, wind_std, total_storms))
        lats = np.random.uniform(24.3, 31.0, total_storms)
        lons = np.random.uniform(-87.8, -79.8, total_storms)

        yearly_losses = []
        storm_idx = 0

        for year in range(sim_years):
            n = poisson.rvs(hurricanes_per_year * climate_factor)
            loss = 0
            for _ in range(n):
                if storm_idx >= total_storms:
                    break
                w = winds[storm_idx]
                c = (lats[storm_idx], lons[storm_idx])
                loss += calculate_loss(df, w, c)[0]
                storm_idx += 1
            yearly_losses.append(loss)

            progress_bar.progress((year + 1) / sim_years)
            status_text.text(f"Simulated {year + 1:,} / {sim_years:,} years")

        progress_bar.empty()
        status_text.empty()

        fig, ax = plt.subplots(figsize=(12,7))
        sorted_losses = sorted(yearly_losses, reverse=True)
        ax.loglog(sorted_losses, np.linspace(1, 0, len(sorted_losses)), color="#f472b6", lw=3)
        ax.axvline(np.mean(yearly_losses), color="#fbbf24", ls="--", lw=2, label=f'EAL: ${np.mean(yearly_losses):,.0f}')
        ax.grid(True, which="both", ls="--", alpha=0.5)
        ax.set_title(f"Exceedance Curve — {sim_years:,} Years", color="white")
        ax.set_xlabel("Annual Loss ($)", color="#e2e8f0")
        ax.set_ylabel("Exceedance Probability", color="#e2e8f0")
        ax.legend()
        st.pyplot(fig)

with tab2:
    st.markdown("#### Hurricane Landfall Animation")
    st.markdown("""
    <div class="explanation">
    The red circle marks the hurricane eye as it moves across Florida over 16 hours.<br>
    Wind speed is shown in the popup and decreases after landfall.
    </div>
    """, unsafe_allow_html=True)

    if st.button("Generate Storm"):
        wind, center = simulate_storm()
        features = []
        lat, lon = center
        for h in range(16):
            lat += np.random.normal(0.04, 0.015)
            lon -= 0.13
            current_wind = max(60, wind - h*5)
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "time": f"2025-09-01T{h:02d}:00:00",
                    "popup": f"Wind: {current_wind:.0f} mph",
                    "icon": "circle",
                    "iconstyle": {"color": "#ec4899", "fillColor": "#ec4899", "weight": 3, "radius": 12}
                }
            })

        m = folium.Map(location=[27.5, -83], zoom_start=7, tiles="CartoDB dark_matter")
        TimestampedGeoJson(
            {"type": "FeatureCollection", "features": features},
            period="PT1H",
            add_last_point=True,
            auto_play=True,
            loop=False
        ).add_to(m)
        folium_static(m, width=900, height=550)

with tab3:
    st.markdown("#### Single Storm Damage Map")
    st.markdown("""
    <div class="explanation">
    Shows one simulated hurricane and its damage footprint.<br>
    • Circle = approximate radius of hurricane-force winds<br>
    • Heat intensity = damage ratio × insured value
    </div>
    """, unsafe_allow_html=True)

    if st.button("Simulate Storm"):
        wind, center = simulate_storm()
        _, impacts = calculate_loss(df, wind, center)

        m = folium.Map(location=[27.8, -83], zoom_start=7, tiles="CartoDB positron")
        CircleMarker(
            location=center,
            radius=wind*800,
            color="#ec4899",
            weight=3,
            fillOpacity=0.2,
            popup=f"{wind:.0f} mph"
        ).add_to(m)
        HeatMap(
            [[lat, lon, dmg*150] for lat, lon, dmg in impacts],
            radius=25, blur=20
        ).add_to(m)
        folium_static(m, width=900, height=550)

# ——————————————————————— Technical Details ———————————————————————
with st.expander("Technical Details & Methodology"):
    st.markdown("""
    - **Frequency**: Poisson(λ × climate factor)  
    - **Intensity**: Normal(μ × climate⁰·⁴, σ), minimum 74 mph  
    - **Location**: Uniform over historical genesis region  
    - **Vulnerability**: Damage = min(1, wind/150 × building factor)  
      Wood ×1.5 | Brick ×1.15 | Concrete ×0.75  
    - **Footprint**: Circular, radius ≈ wind speed × 0.5 km  
    - **Aggregation**: Sum of all storm losses per year  
    - **Exceedance curve**: Rank-ordered annual losses
    """)

st.markdown("<p style='text-align:center; color:#64748b; margin-top:4rem;'>Built with Streamlit • Open source • November 2025</p>", unsafe_allow_html=True)