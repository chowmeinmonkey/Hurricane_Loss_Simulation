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
from folium import Circle  # ← This was the fix!
from scipy.stats import poisson

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
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #ec4899, #f59e0b);
        color: white;
    }
    .block-container {padding-top: 2rem; max-width: 1400px;}
    .explanation {
        background: rgba(236, 72, 153, 0.08);
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 4px solid #ec4899;
        margin: 1.5rem 0;
        font-size: 0.98rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# ——————————————————————— Portfolio ———————————————————————
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
            total += row.insured_value * dmg
            impacts.append((row.lat, row.lon, dmg))
        else:
            impacts.append((row.lat, row.lon, 0))
    return total, impacts

# ——————————————————————— Header ———————————————————————
st.markdown("""
<div style="text-align:center;padding:4rem 2rem;background:linear-gradient(135deg,rgba(236,72,153,0.15),rgba(245,158,11,0.15));border-radius:20px;border:1px solid rgba(236,72,153,0.3);margin-bottom:3rem;">
    <h1 style="font-size:4.5rem;margin:0;">Hurricane Risk Lab</h1>
    <p style="font-size:1.5rem;color:#cbd5e1;max-width:900px;margin:1.5rem auto;line-height:1.6;">
        Interactive catastrophe modeling for Florida — explore how storm frequency, intensity, and climate change affect insured losses.
    </p>
</div>
""", unsafe_allow_html=True)

# ——————————————————————— Sidebar ———————————————————————
with st.sidebar:
    st.header("Simulation Controls")
    hurricanes_per_year = st.slider("Hurricanes per year (λ)", 0.1, 10.0, 0.56, 0.05)
    wind_mean = st.slider("Mean wind speed (mph)", 80, 180, 110, 5)
    wind_std = st.slider("Wind speed std dev (mph)", 10, 50, 25, 5)
    sim_years = st.slider("Years to simulate", 5_000, 50_000, 20_000, 5_000)

    st.markdown("---")
    st.subheader("Climate Scenario")
    climate = st.select_slider("Year", options=["Today", "2030", "2050", "2100"], value="Today")
    climate_factor = {"Today": 1.0, "2030": 1.12, "2050": 1.25, "2100": 1.45}[climate]
    st.markdown(f"**Multiplier: ×{climate_factor:.2f}**")

# ——————————————————————— Live Dashboard ———————————————————————
st.markdown("### Live Risk Dashboard")

@st.cache_data(ttl=30)
def quick_sim():
    losses = []
    for _ in range(250):
        n = poisson.rvs(hurricanes_per_year * climate_factor)
        year_loss = 0
        for _ in range(n):
            w = max(74, np.random.normal(wind_mean * climate_factor**0.4, wind_std))
            c = simulate_storm()[1]
            year_loss += calculate_loss(df, w, c)[0]
        losses.append(year_loss)
    return np.array(losses)

losses = quick_sim()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Expected Annual Loss</div><div class="metric-value">${losses.mean():,.0f}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">99% VaR</div><div class="metric-value">${np.quantile(losses,0.99):,.0f}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Prob > $10M</div><div class="metric-value">{(losses>10e6).mean():.1%}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Climate Multiplier</div><div class="metric-value">×{climate_factor:.2f}</div></div>', unsafe_allow_html=True)

# ——————————————————————— Tabs ———————————————————————
tab1, tab2, tab3 = st.tabs(["Loss Curve", "Animated Storm", "Damage Heatmap"])

with tab1:
    st.markdown("##### Loss Exceedance Curve")
    st.markdown("""
    <div class="explanation">
    <strong>What you’re seeing:</strong><br>
    • X-axis = Annual insured loss in dollars<br>
    • Y-axis = Probability of exceeding that loss in any given year<br>
    • 1% = a 1-in-100-year event<br>
    • Yellow dashed line = Expected Annual Loss
    </div>
    """, unsafe_allow_html=True)

    if st.button("Run Simulation", type="primary"):
        with st.spinner(f"Simulating {sim_years:,} years..."):
            total_storms = int(sim_years * hurricanes_per_year * climate_factor * 1.5)
            winds = np.maximum(74, np.random.normal(wind_mean * climate_factor**0.4, wind_std, total_storms))
            lat = np.random.uniform(24.3, 31.0, total_storms)
            lon = np.random.uniform(-87.8, -79.8, total_storms)

            yearly_losses = []
            idx = 0
            for _ in range(sim_years):
                n = poisson.rvs(hurricanes_per_year * climate_factor)
                loss = 0
                for _ in range(n):
                    if idx >= total_storms: break
                    loss += calculate_loss(df, winds[idx], (lat[idx], lon[idx]))[0]
                    idx += 1
                yearly_losses.append(loss)

            fig, ax = plt.subplots(figsize=(12,7))
            sorted_l = sorted(yearly_losses, reverse=True)
            ax.loglog(sorted_l, np.linspace(1, 0, len(sorted_l)), color="#f472b6", lw=3)
            ax.axvline(np.mean(yearly_losses), color='#fbbf24', linestyle='--', linewidth=2,
                       label=f'Expected Loss: ${np.mean(yearly_losses):,.0f}')
            ax.grid(True, which="both", ls="--", alpha=0.5)
            ax.set_title(f"Loss Exceedance Curve — {sim_years:,} Years", color="white", fontsize=18)
            ax.set_xlabel("Annual Loss ($)", color="#e2e8f0")
            ax.set_ylabel("Exceedance Probability", color="#e2e8f0")
            ax.legend()
            st.pyplot(fig)

with tab2:
    st.markdown("##### Watch a Hurricane Make Landfall")
    st.markdown("""
    <div class="explanation">
    <strong>How the animation works:</strong><br>
    • Random hurricane forms in the Gulf or Atlantic<br>
    • Moves northwest at realistic speed (~15 mph)<br>
    • Wind speed decays after landfall<br>
    • Red dot = eye position hour-by-hour
    </div>
    """, unsafe_allow_html=True)

    if st.button("Launch Hurricane"):
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
    st.markdown("""
    <div class="explanation">
    <strong>How damage is calculated:</strong><br>
    • Storm radius ≈ wind speed × 0.5 km<br>
    • Buildings inside radius take damage based on wind & construction type<br>
    • Wood = 50% more vulnerable than concrete<br>
    • Heat intensity = damage × insured value
    </div>
    """, unsafe_allow_html=True)

    if st.button("Generate Storm Impact"):
        wind, center = simulate_storm()
        _, impacts = calculate_loss(df, wind, center)
        m = folium.Map(location=[27.8, -83], zoom_start=7, tiles="CartoDB positron")
        Circle(location=center, radius=wind*1000, color="#ec4899", weight=3, fill_opacity=0.25).add_to(m)
        HeatMap([[lat, lon, dmg*120] for lat, lon, dmg in impacts], radius=25, blur=20).add_to(m)
        folium_static(m, width=900, height=550)

# ——————————————————————— Math Section ———————————————————————
with st.expander("How the Math Works — Technical Details", expanded=False):
    st.markdown("""
    ### Monte-Carlo Catastrophe Modeling (industry standard)

    1. **Frequency** — Poisson(λ × climate factor)  
    2. **Intensity** — Normal(μ × climate^0.4, σ)  
    3. **Location** — Uniform in historical zone  
    4. **Vulnerability** — Damage = min(1, wind/150 × building factor)  
    5. **Footprint** — Circular radius = wind × 0.5 km  
    6. **Aggregation** — Sum all storm losses per year  
    7. **Exceedance** — Rank-order annual losses

    Same core method used by RMS, AIR, and reinsurers — just fast and beautiful.
    """)

# ——————————————————————— Footer ———————————————————————
st.markdown("""
<div style="text-align:center;margin-top:6rem;padding:2rem;background:rgba(236,72,153,0.08);border-radius:16px;">
</div>
""", unsafe_allow_html=True)