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
import plotly.graph_objects as go
from scipy.stats import poisson, norm

# ——————————————————————————————————————————————
# Page Config & Professional Styling
# ——————————————————————————————————————————————

st.set_page_config(page_title="Hurricane Risk Lab", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    body, .css-18e3th9, .css-1d391kg {font-family: 'Inter', sans-serif;}
    .main {background: #0f172a; color: #e2e8f0;}
    
    h1 {color: #f472b6; font-weight: 700; margin-bottom: 0.5rem;}
    h2, h3 {color: #fbbf24; font-weight: 600;}
    
    .stApp {background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);}
    
    /* Metric cards */
    .metric-card {
        background: rgba(251, 191, 36, 0.12);
        border: 1px solid rgba(251, 191, 36, 0.25);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        height: 140px;
    }
    .metric-label {font-size: 0.95rem; color: #94a3b8; margin-bottom: 0.5rem;}
    .metric-value {font-size: 1.8rem; font-weight: 700; color: #fbbf24;}
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #ec4899, #f59e0b);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);
        transition: all 0.3s;
        width: 100%;
        height: 50px;
    }
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(236, 72, 153, 0.6);
    }
    
    /* Tabs */
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
    
    /* Fix spacing */
    .block-container {padding-top: 2rem; max-width: 1400px;}
    .css-1y0t9h3 {padding: 1rem;}
</style>
""", unsafe_allow_html=True)

# ——————————————————————————————————————————————
# Demo Portfolio Data
# ——————————————————————————————————————————————

@st.cache_data
def get_demo_portfolio():
    return pd.DataFrame({
        "property_id": range(1, 9),
        "city": ["Miami", "Tampa", "Tallahassee", "Orlando", "Ft Lauderdale", "Jacksonville", "Key West", "Pensacola"],
        "insured_value": [500000, 750000, 1000000, 600000, 800000, 1200000, 450000, 900000],
        "construction_type": ["wood", "brick", "concrete", "wood", "brick", "concrete", "wood", "concrete"],
        "lat": [25.7617, 27.9478, 30.4383, 28.5383, 26.1224, 30.3322, 24.5551, 30.4213],
        "lon": [-80.1918, -82.4584, -84.2807, -81.3792, -80.1373, -81.6557, -81.7799, -87.2169]
    })

exposure_df = get_demo_portfolio()

# ——————————————————————————————————————————————
# Core Modeling Functions
# ——————————————————————————————————————————————

def vulnerability_curve(wind_speed_mph: float, construction: str = "average") -> float:
    """Return damage ratio (0–1) based on wind speed and building type."""
    base_damage = max(0.0, min(1.0, wind_speed_mph / 150))
    multipliers = {"wood": 1.50, "brick": 1.15, "concrete": 0.75}
    return min(1.0, base_damage * multipliers.get(construction.lower(), 1.0))

def simulate_storm_center():
    return (np.random.uniform(24.3, 31.0), np.random.uniform(-87.8, -79.8))

def simulate_wind_speed(mean_mph: float = 110):
    return max(74, np.random.normal(mean_mph, 25))

def calculate_portfolio_loss(df, wind_speed, center):
    radius_km = wind_speed * 0.5
    total_loss = 0
    impacts = []
    
    for _, row in df.iterrows():
        distance_km = ((row.lat - center[0])**2 + (row.lon - center[1])**2)**0.5 * 111
        if distance_km <= radius_km:
            damage_ratio = vulnerability_curve(wind_speed, row.construction_type)
            loss = row.insured_value * damage_ratio
            total_loss += loss
            impacts.append((row.lat, row.lon, damage_ratio))
        else:
            impacts.append((row.lat, row.lon, 0))
    return total_loss, impacts

# ——————————————————————————————————————————————
# Header
# ——————————————————————————————————————————————

st.markdown("""
<div style="text-align:center; padding:4rem 2rem; background:linear-gradient(135deg,rgba(236,72,153,0.15),rgba(245,158,11,0.15)); border-radius:20px; border:1px solid rgba(236,72,153,0.3); margin-bottom:3rem;">
    <h1 style="font-size:4.2rem; margin:0;">Hurricane Risk Lab</h1>
    <p style="font-size:1.4rem; color:#cbd5e1; margin-top:1rem;">
        Interactive catastrophe modeling 
    </p>
</div>
""", unsafe_allow_html=True)

# ——————————————————————————————————————————————
# Sidebar ———————— SIDEBAR: Full Controls ————————
# ——————————————————————————————————————————————

with st.sidebar:
    st.header("Simulation Parameters")
    
    col_a, col_b = st.columns(2)
    with col_a:
        hurricanes_per_year = st.number_input("Hurricanes/year (λ)", 0.1, 10.0, 0.56, 0.05)
        wind_mean = st.slider("Mean wind speed (mph)", 80, 180, 110, 5)
    with col_b:
        wind_variation = st.slider("Wind speed std dev", 10, 50, 25, 5)
        damage_threshold = st.slider("Damage threshold (mph)", 100, 200, 150, 5)
    
    st.markdown("---")
    st.subheader("Climate Scenario")
    climate = st.select_slider("Future climate impact", 
                               options=["Today", "2030", "2050", "2100"], 
                               value="Today")
    climate_factor = {"Today": 1.0, "2030": 1.12, "2050": 1.25, "2100": 1.45}[climate]
    
    st.markdown(f"**Intensity multiplier: ×{climate_factor:.2f}**")
    
    st.markdown("---")
    st.subheader("Portfolio")
    uploaded = st.file_uploader("Upload your own CSV", type=["csv"],
                                help="Must have: insured_value, lat, lon. Optional: construction_type, city")
    if uploaded:
        try:
            user_df = pd.read_csv(uploaded)
            required = ['insured_value', 'lat', 'lon']
            if all(c in user_df.columns for c in required):
                exposure_df = user_df
                st.success(f"Loaded {len(exposure_df):,} properties")
                st.balloons()
            else:
                st.error(f"Missing columns: {set(required) - set(user_df.columns)}")
        except:
            st.error("Could not read CSV")

# ——————————————————————————————————————————————
# Live Risk Dashboard
# ——————————————————————————————————————————————

st.markdown("### Live Risk Dashboard")

# Fast simulation for live metrics
@st.cache_data(ttl=60)
def run_quick_simulation():
    losses = []
    for _ in range(500):
        n_events = poisson.rvs(hurricanes_per_year * climate_factor)
        annual_loss = 0
        for _ in range(n_events):
            wind = simulate_wind_speed(wind_mean * climate_factor**0.4)
            center = simulate_storm_center()
            loss, _ = calculate_portfolio_loss(exposure_df, wind, center)
            annual_loss += loss
        losses.append(annual_loss)
    return losses

losses = run_quick_simulation()

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

# ——————————————————————————————————————————————
# Main Tabs
# ——————————————————————————————————————————————

tab1, tab2, tab3, tab4 = st.tabs(["Loss Exceedance Curve", "Animated Storm Track", "3D Wind Field", "Damage Heatmap"])

with tab1:
    st.markdown("##### Full Monte Carlo Simulation (50,000 years)")
    if st.button("Run 50,000-Year Simulation", type="primary"):
        with st.spinner("Simulating half a century of hurricanes..."):
            full_losses = []
            for _ in range(50000):
                events = poisson.rvs(hurricanes_per_year * climate_factor)
                year_loss = sum(
                    calculate_portfolio_loss(exposure_df,
                                            simulate_wind_speed(wind_mean * climate_factor**0.4),
                                            simulate_storm_center())[0]
                    for _ in range(events)
                )
                full_losses.append(year_loss or 0)
            
            fig, ax = plt.subplots(figsize=(12, 7))
            ax.loglog(sorted(full_losses, reverse=True), 
                     np.linspace(1, 0, len(full_losses)), 
                     color="#f472b6", linewidth=3)
            ax.grid(True, which="both", ls="--", alpha=0.5, color="#475569")
            ax.set_title("Loss Exceedance Curve", fontsize=18, color="white")
            ax.set_xlabel("Annual Loss ($)", color="#e2e8f0")
            ax.set_ylabel("Exceedance Probability", color="#e2e8f0")
            st.pyplot(fig)

with tab2:
    st.markdown("##### Watch a Hurricane Make Landfall")
    if st.button("Generate Animated Storm"):
        wind, (lat0, lon0) = simulate_storm_center(), simulate_wind_speed(wind_mean)
        track = []
        lat, lon = lat0, lon0
        for h in range(16):
            lat += np.random.normal(0.04, 0.015)
            lon -= 0.13
            wind_now = max(60, wind - h*5)
            track.append((lat, lon, wind_now))
        
        features = [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [ln, lt]},
             "properties": {"time": f"2025-09-01T{h:02d}:00:00", "popup": f"{w:.0f} mph", "icon": "circle"}}
            for h, (lt, ln, w) in enumerate(track)
        ]
        
        m = folium.Map(location=[27.5, -83], zoom_start=7, tiles="CartoDB dark_matter")
        TimestampedGeoJson({"type": "FeatureCollection", "features": features},
                           period="PT1H", add_last_point=True, auto_play=True, loop=False).add_to(m)
        folium_static(m, width=900, height=550)

with tab3:
    st.markdown("##### 3D Wind Speed Surface")
    if st.button("Render 3D Wind Field"):
        wind, center = simulate_wind_speed(wind_mean), simulate_storm_center()
        x = np.linspace(center[1]-3, center[1]+3, 70)
        y = np.linspace(center[0]-3, center[0]+3, 70)
        X, Y = np.meshgrid(x, y)
        Z = wind * np.exp(-((X-center[1])**2 + (Y-center[0])**2) / 2.5)
        
        fig = go.Figure(data=[go.Surface(z=Z, x=X, y=Y, colorscale="OrRd", showscale=False)])
        fig.update_layout(scene=dict(xaxis_title="Longitude", yaxis_title="Latitude", zaxis_title="Wind Speed"),
                          margin=dict(l=0,r=0,b=0,t=40), height=650,
                          paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown("##### Real-Time Damage Heatmap")
    if st.button("Generate Current Storm Impact"):
        wind, center = simulate_wind_speed(wind_mean), simulate_storm_center()
        _, impacts = calculate_portfolio_loss(exposure_df, wind, center)
        
        m = folium.Map(location=[27.8, -83], zoom_start=7, tiles="CartoDB positron")
        folium.Circle(location=center, radius=wind*1000, color="#ec4899", weight=3, fill_opacity=0.25).add_to(m)
        HeatMap([[lat, lon, dmg*120] for lat, lon, dmg in impacts], radius=25, blur=20).add_to(m)
        folium_static(m, width=900, height=550)

# ——————————————————————————————————————————————
# Footer
# ——————————————————————————————————————————————

st.markdown("""
<div style="text-align:center; margin-top:6rem; padding:2rem; background:rgba(236,72,153,0.08); border-radius:16px; border:1px solid rgba(236,72,153,0.2);">
</div>
""", unsafe_allow_html=True)