# =======================================================
#   FLORIDA HURRICANE RISK LAB 
# =======================================================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
from folium.plugins import TimestampedGeoJson, HeatMap
import plotly.graph_objects as go
from scipy.stats import poisson, norm

# ———————————————— PAGE LOOKS AMAZING ————————————————
st.set_page_config(page_title="Hurricane Risk Lab", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    body {font-family: 'Inter', sans-serif;}
    .main {background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);}
    h1 {color: #f472b6 !important; font-weight: 700;}
    h2, h3 {color: #fbbf24;}
    
    .css-1d391kg {padding-top: 2rem;}
    
    .metric-box {
        background: rgba(251, 191, 36, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(251, 191, 36, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #ec4899, #f59e0b);
        color: white;
        border: none;
        border-radius: 12px;
        height: 3rem;
        font-weight: 600;
        box-shadow: 0 4px 20px rgba(236, 72, 153, 0.4);
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 30px rgba(236, 72, 153, 0.6);
    }
    
    .stTabs [data-baseweb="tab-list"] {gap: 12px;}
 .stTabs [data-baseweb="tab"] {
     background: rgba(255,255,255,0.05);
     border-radius: 12px;
     padding: 12px 24px;
     color: #94a3b8;
 }
 .stTabs [aria-selected="true"] {
     background: linear-gradient(90deg, #ec4899, #f59e0b);
     color: white !important;
 }
</style>
""", unsafe_allow_html=True)

# ———————————————— BUILT-IN DATA ————————————————
@st.cache_data
def load_demo_data():
    return pd.DataFrame({
        "property_id": [1, 2, 3, 4, 5, 6, 7, 8],
        "city": ["Miami", "Tampa", "Tampa", "Tallahassee", "Orlando", "Ft Lauderdale", "Jacksonville", "Key West", "Pensacola"],
        "insured_value": [500000, 750000, 1000000, 600000, 800000, 1200000, 450000, 900000],
        "construction_type": ["wood", "brick", "concrete", "wood", "brick", "concrete", "wood", "concrete"],
        "lat": [25.7617, 27.9478, 30.4383, 28.5383, 26.1224, 30.3322, 24.5551, 30.4213],
        "lon": [-80.1918, -82.4584, -84.2807, -81.3792, -80.1373, -81.6557, -81.city7799, -87.2169]
    })

exposure_df = load_demo_data()

# ———————————————— CORE MODEL ————————————————
def vulnerability(wind_mph, construction="average"):
    base = max(0, min(1, wind_mph / 150))
    mult = {"wood": 1.5, "brick": 1.15, "concrete": 0.75}
    return min(1.0, base * mult.get(construction.lower(), 1.0))

def simulate_storm():
    center = (np.random.uniform(24.3, 31.0), np.random.uniform(-87.8, -79.8))
    wind = max(74, np.random.normal(104, 25))
    return wind, center

def calculate_portfolio_loss(df, wind, center):
    radius = wind * 0.5
    total = 0
    hits = []
    for _, row in df.iterrows():
        dist = ((row.lat - center[0])**2 + (row.lon - center[1])**2)**0.5 * 111
        if dist <= radius:
            dmg = vulnerability(wind, row.construction_type)
            loss = row.insured_value * dmg
            total += loss
            hits.append((row.lat, row.lon, dmg))
        else:
            hits.append((row.lat, row.lon, 0))
    return total, hits

# ———————————————— HEADER ————————————————
st.markdown("""
<div style="text-align:center; padding:3rem 1rem; background: linear-gradient(90deg, rgba(236,72,153,0.2), rgba(245,158,11,0.2)); border-radius:20px; border:1px solid rgba(236,72,153,0.3);">
    <h1 style="font-size:4rem; margin:0;">Hurricane Risk Lab</h1>
    <p style="font-size:1.4rem; opacity:0.9; margin:1rem 0;">Real-time catastrophe modeling · Animated storms · 3D visualization</p>
</div>
""", unsafe_allow_html=True)

# ———————————————— SIDEBAR ————————————————
with st.sidebar:
    st.markdown("<h2 style='color:#f472b6'>Simulation Controls</h2>", unsafe_allow_html=True)
    
    lambda_rate = st.slider("Hurricanes per year", 0.1, 6.0, 0.56, 0.1)
    wind_mean = st.slider("Mean wind speed (mph)", 80, 180, 110)
    climate = st.select_slider("Climate Scenario", ["Today" → "2050"]", options=["Today", "2030", "2050"], value="Today")
    climate_mult = {"Today": 1.0, "2030": 1.12, "2050": 1.25}[climate]
    
    uploaded = st.file_uploader("Or upload your own portfolio (CSV)", type="csv")
    if uploaded:
        try:
            exposure_df = pd.read_csv(uploaded)
            st.success(f"Loaded {len(exposure_df):,} properties")
            st.balloons()
        except:
            st.error("Invalid CSV")

# ——————————————— LIVE METRICS ———————————————
st.markdown("### Live Risk Snapshot")
losses = []
for _ in range(300):
    n_storms = poisson.rvs(lambda_rate * climate_mult)
    year_loss = 0
    for _ in range(n_storms):
        w, c = simulate_storm()
        w *= climate_mult**0.5
        loss, _ = calculate_portfolio_loss(exposure_df, w, c)
        year_loss += loss
    losses.append(year_loss)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-box"><h4>Expected Annual Loss</h4><h2>${np.mean(losses):,.0f}</h2></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-box"><h4>99% VaR</h4><h2>${np.quantile(losses,0.99):,.0f}</h2></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-box"><h4>Prob > $10M</h4><h2>{(np.array(losses)>10e6).mean():.1%}</h2></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-box"><h4>Climate Factor</h4><h2>×{climate_mult:.2f}</h2></div>', unsafe_allow_html=True)

# ———————————————— TABS ————————————————
tab1, tab2, tab3, tab4 = st.tabs(["Loss Exceedance", "Animated Storm", "3D Wind Field", "Damage Heatmap"])

with tab1:
    if st.button("Run 50,000-Year Simulation", type="primary"):
        with st.spinner("Simulating half a century of storms..."):
            big = []
            for _ in range(50000):
                n = poisson.rvs(lambda_rate * climate_mult)
                y = sum(calculate_portfolio_loss(exposure_df, 
                        sample_wind_speed(wind_mean * climate_mult**0.5, 25), 
                        simulate_hurricane_center())[0] for _ in range(n))
                big.append(y or 0)
            fig, ax = plt.subplots(figsize=(12,7))
            ax.loglog(sorted(big, reverse=True), np.linspace(1, 0, len(big)), color="#f472b6", lw=3)
            ax.grid(True, which="both", ls="--", alpha=0.5)
            ax.set_title("Loss Exceedance Curve", fontsize=18, color="white")
            ax.set_xlabel("Loss ($)", color="#cbd5e1")
            ax.set_ylabel("Probability", color="#cbd5e1")
            st.pyplot(fig, use_container_width=True)

with tab2:
    if st.button("Launch Animated Hurricane"):
        wind, (lat0, lon0) = simulate_storm()
        track = []
        lat, lon = lat0, lon0
        for h in range(16):
            lat += np.random.normal(0.04, 0.02)
            lon -= 0.13
            wind_now = max(60, wind - h*5)
            track.append((lat, lon, wind_now))
        
        features = [{"type":"Feature","geometry":{"type":"Point","coordinates":[ln,lt]},
                     "properties":{"time":f"2025-09-01T{h:02d}:00:00","popup":f"{w:.0f} mph","icon":"circle"}}
                    for h, (lt, ln, w) in enumerate(track)]
        
        m = folium.Map(location=[27.5, -83], zoom_start=7, tiles="CartoDB dark_matter")
        TimestampedGeoJson({"type":"FeatureCollection","features":features},
                           period="PT1H", add_last_point=True, auto_play=True, loop=False).add_to(m)
        folium_static(m, width=900, height=550)

with tab3:
    if st.button("Render 3D Wind Field"):
        wind, center = simulate_storm()
        x = np.linspace(center[1]-3, center[1]+3, 60)
        y = np.linspace(center[0]-3, center[0]+3, 60)
        X, Y = np.meshgrid(x, y)
        Z = wind * np.exp(-((X-center[1])**2 + (Y-center[0])**2) / 2)
        
        fig = go.Figure(data=[go.Surface(z=Z, x=X, y=Y, colorscale="OrRd", showscale=False)])
        fig.update_layout(scene=dict(xaxis_title="Longitude", yaxis_title="Latitude", zaxis_title="Wind (mph)"),
                          margin=dict(l=0,r=0,b=0,t=40), height=600,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    if st.button("Generate Damage Heatmap"):
        wind, center = simulate_storm()
        _, impacts = calculate_portfolio_loss(exposure_df, wind, center)
        
        m = folium.Map(location=[27.8, -83], zoom_start=7, tiles="CartoDB positron")
        folium.Circle(location=center, radius=wind*1000, color="#ec4899", weight=3, fill=True, opacity=0.2).add_to(m)
        HeatMap([[lat, lon, dmg*100] for lat, lon, dmg in impacts], radius=22, blur=18).add_to(m)
        folium_static(m, width=900, height=550)

# ———————————————— FOOTER ————————————————
st.markdown("""
<div style="text-align:center; margin-top:6rem; padding:2rem; background:rgba(236,72,153,0.1); border-radius:16px;">
    <p style="font-size:1.1rem; opacity:0.8;">
        Built with <strong>Streamlit</strong> • Open source • Made by a human who cares about beautiful risk tools
    </p>
</div>
""", unsafe_allow_html=True)