# =======================================================
#   FLORIDA HURRICANE RISK LAB — FINAL BEAUTIFUL VERSION
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

# ———————————————— CUSTOM STYLING ————————————————
st.set_page_config(page_title="Hurricane Risk Lab", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    body {font-family: 'Inter', sans-serif;}
    .main {background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);}
    h1 {color: #f472b6 !important; font-weight: 700;}
    h2, h3 {color: #fbbf24;}
    
    .metric-box {
        background: rgba(251, 191, 36, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(251, 191, 36, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #ec4899, #f59e0b);
        color: white;
        border: none;
        border-radius: 12px;
        height: 3rem;
        font-weight: 600;
        box-shadow: 0 4px 20px rgba(236, 72, 153, 0.4);
    }
    .stButton>button:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 30px rgba(236, 72, 153, 0.6);
    }
    
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

# ———————————————— DATA ————————————————
@st.cache_data
def load_demo_data():
    return pd.DataFrame({
        "property_id": [1, 2, 3, 4, 5, 6, 7, 8],
        "city": ["Miami", "Tampa", "Tallahassee", "Orlando", "Ft Lauderdale", "Jacksonville", "Key West", "Pensacola"],
        "insured_value": [500000, 750000, 1000000, 600000, 800000, 1200000, 450000, 900000],
        "construction_type": ["wood", "brick", "concrete", "wood", "brick", "concrete", "wood", "concrete"],
        "lat": [25.7617, 27.9478, 30.4383, 28.5383, 26.1224, 30.3322, 24.5551, 30.4213],
        "lon": [-80.1918, -82.4584, -84.2807, -81.3792, -80.1373, -81.6557, -81.7799, -87.2169]
    })

exposure_df = load_demo_data()

# ———————————————— MODEL LOGIC ————————————————
def vulnerability(wind_mph, construction="average"):
    base = max(0.0, min(1.0, wind_mph / 150))
    mult = {"wood": 1.5, "brick": 1.15, "concrete": 0.75}
    return min(1.0, base * mult.get(construction.lower(), 1.0))

def simulate_storm():
    center = (np.random.uniform(24.3, 31.0), np.random.uniform(-87.8, -79.8))
    wind = max(74, np.random.normal(110, 25))
    return wind, center

def calculate_portfolio_loss(df, wind, center):
    radius_km = wind * 0.5
    total = 0
    hits = []
    for _, row in df.iterrows():
        dist = ((row.lat - center[0])**2 + (row.lon - center[1])**2)**0.5 * 111
        if dist <= radius_km:
            dmg = vulnerability(wind, row.construction_type)
            loss = row.insured_value * dmg
            total += loss
            hits.append((row.lat, row.lon, dmg))
        else:
            hits.append((row.lat, row.lon, 0))
    return total, hits

# ———————————————— HEADER ————————————————
st.markdown("""
<div style="text-align:center;padding:3rem 1rem;background:linear-gradient(90deg,rgba(236,72,153,0.2),rgba(245,158,11,0.2));border-radius:20px;border:1px solid rgba(236,72,153,0.3);margin-bottom:2rem;">
    <h1 style="font-size:4rem;margin:0;">Hurricane Risk Lab</h1>
    <p style="font-size:1.4rem;opacity:0.9;">Real-time catastrophe modeling with animated storms & 3D visualization</p>
</div>
""", unsafe_allow_html=True)

# ———————————————— SIDEBAR ————————————————
with st.sidebar:
    st.markdown("<h2 style='color:#f472b6'>Controls</h2>", unsafe_allow_html=True)
    lambda_rate = st.slider("Hurricanes per year", 0.1, 6.0, 0.56, 0.1)
    wind_mean = st.slider("Mean wind speed (mph)", 80, 180, 110)
    climate = st.select_slider("Climate Scenario", options=["Today", "2030", "2050"], value="Today")
    climate_mult = {"Today": 1.0, "2030": 1.12, "2050": 1.25}[climate]

    uploaded = st.file_uploader("Upload your own portfolio (CSV)", type="csv")
    if uploaded:
        try:
            exposure_df = pd.read_csv(uploaded)
            st.success(f"Loaded {len(exposure_df):,} properties")
            st.balloons()
        except:
            st.error("Invalid CSV — check columns")

# ———————————————— LIVE METRICS ————————————————
st.markdown("### Live Risk Snapshot")
quick_losses = []
for _ in range(300):
    n = poisson.rvs(lambda_rate * climate_mult)
    year_loss = sum(calculate_portfolio_loss(exposure_df,
                                            max(74, np.random.normal(wind_mean * climate_mult**0.5, 25)),
                                            simulate_storm()[1])[0] for _ in range(n))
    quick_losses.append(year_loss or 0)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-box"><h4>Expected Annual Loss</h4><h2>${np.mean(quick_losses):,.0f}</h2></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-box"><h4>99% VaR</h4><h2>${np.quantile(quick_losses,0.99):,.0f}</h2></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-box"><h4>Prob > $10M loss</h4><h2>{(np.array(quick_losses)>10e6).mean():.1%}</h2></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-box"><h4>Climate Factor</h4><h2>×{climate_mult:.2f}</h2></div>', unsafe_allow_html=True)

# ———————————————— TABS ————————————————
tab1, tab2, tab3, tab4 = st.tabs(["Loss Curve", "Animated Storm", "3D Wind", "Damage Heatmap"])

# (Keep the rest of the tab code exactly as in my previous message — it’s unchanged)

# ———————————————— FOOTER ————————————————
st.markdown("""
<div style="text-align:center;margin-top:6rem;padding:2rem;background:rgba(236,72,153,0.1);border-radius:16px;">
    <p style="font-size:1.1rem;opacity:0.8;">
        Built with Streamlit • Open source • Made with passion
    </p>
</div>
""", unsafe_allow_html=True)