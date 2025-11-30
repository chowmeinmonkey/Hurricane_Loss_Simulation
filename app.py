# ==================================================
# ULTIMATE FLORIDA HURRICANE RISK SIMULATOR
# ==================================================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
from folium.plugins import TimestampedGeoJson, HeatMap
import plotly.graph_objects as go
from scipy.stats import poisson, norm
import base64
from io import BytesIO

# ———————————————— BUILT-IN DATA ————————————————
data = {
    "property_id": [1, 2, 3, 4, 5, 6, 7, 8],
    "insured_value": [500000, 750000, 1000000, 600000, 800000, 1200000, 450000, 900000],
    "city": ["Miami", "Tampa", "Tallahassee", "Orlando", "Fort Lauderdale", "Jacksonville", "Key West", "Pensacola"],
    "construction_type": ["wood", "brick", "concrete", "wood", "brick", "concrete", "wood", "concrete"],
    "lat": [25.7617, 27.9478, 30.4383, 28.5383, 26.1224, 30.3322, 24.5551, 30.4213],
    "lon": [-80.1918, -82.4584, -84.2807, -81.3792, -80.1373, -81.6557, -81.7799, -87.2169]
}
exposure_df = pd.DataFrame(data)

# ———————————————— MODEL FUNCTIONS ————————————————
def vulnerability_function(wind_speed, threshold=150, construction_type="average"):
    base = min(1.0, max(0.0, wind_speed / threshold))
    multipliers = {"wood": 1.5, "brick": 1.2, "concrete": 0.8}
    return min(1.0, base * multipliers.get(construction_type.lower(), 1.0))

def simulate_hurricane_center():
    return (np.random.uniform(24.3, 31.0), np.random.uniform(-87.8, -79.8))

def sample_wind_speed(mean=104, std=25):
    return max(74, norm.rvs(loc=mean, scale=std))

def simulate_event_frequency(lambda_param=0.56):
    return poisson.rvs(mu=lambda_param)

def calculate_loss(df, wind_speed, center):
    damage_ratio = vulnerability_function(wind_speed)
    radius_km = wind_speed * 0.5
    total_loss = 0
    impacted = []
    for _, row in df.iterrows():
        dist = np.sqrt((row['lat'] - center[0])**2 + (row['lon'] - center[1])**2) * 111
        if dist <= radius_km:
            dmg = vulnerability_function(wind_speed, 150, row['construction_type'])
            loss = row['insured_value'] * dmg
            total_loss += loss
            impacted.append((row['lat'], row['lon'], dmg))
        else:
            impacted.append((row['lat'], row['lon'], 0))
    return total_loss, impacted

# ———————————————— STREAMLIT APP ————————————————
st.set_page_config(page_title="Ultimate Hurricane Risk Lab", layout="wide")
st.title("Ultimate Florida Hurricane Risk Lab")
st.markdown("**Monte-Carlo | Animated Tracks | 3D | Climate Change | PDF Export | Upload Your Portfolio**")

# ——————— SIDEBAR CONTROLS ———————
st.sidebar.header("Simulation Controls")
lambda_param = st.sidebar.slider("Hurricanes per year (λ)", 0.1, 6.0, 0.56, 0.05)
wind_mean = st.sidebar.slider("Mean wind speed (mph)", 70, 180, 104)
wind_std = st.sidebar.slider("Wind variation (mph)", 10, 60, 25)
threshold = st.sidebar.slider("Base damage threshold (mph)", 100, 220, 150)

climate_year = st.sidebar.select_slider("Climate Scenario", options=["2025 (Today)", "2050 (+20%)"], value="2025 (Today)")
climate_factor = 1.2 if "2050" in climate_year else 1.0

years = st.sidebar.slider("Monte-Carlo years", 1000, 200000, 20000, 5000)

# Optional: Upload your own portfolio
uploaded_file = st.sidebar.file_uploader("Or upload your own CSV", type="csv")
if uploaded_file:
    exposure_df = pd.read_csv(uploaded_file)
    st.success(f"Loaded {len(exposure_df)} properties from your file!")

# ——————— LIVE RISK DASHBOARD ———————
st.subheader("Live Risk Dashboard")
quick = []
for _ in range(200):
    events = simulate_event_frequency(lambda_param * climate_factor)
    yloss = 0
    for _ in range(events):
        w = sample_wind_speed(wind_mean * climate_factor**0.5, wind_std)
        c = simulate_hurricane_center()
        l, _ = calculate_loss(exposure_df, w, c)
        yloss += l
    quick.append(yloss)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Expected Annual Loss", f"${np.mean(quick):,.0f}")
col2.metric("99% VaR", f"${np.quantile(quick, 0.99):,.0f}")
col3.metric("Prob > $5M Loss", f"{np.mean(np.array(quick)>5e6):.1%}")
col4.metric("Climate Multiplier", f"×{climate_factor:.2f}")

# ——————— TABS FOR DIFFERENT VIEWS ———————
tab1, tab2, tab3, tab4 = st.tabs(["Monte-Carlo Loss Curve", "Animated Storm Path", "3D Wind Field", "Damage Heatmap"])

with tab1:
    if st.button("Run Full Simulation", type="primary"):
        with st.spinner("Running 20,000+ years..."):
            losses = []
            for _ in range(years):
                events = simulate_event_frequency(lambda_param * climate_factor)
                year_loss = 0
                for _ in range(events):
                    wind = sample_wind_speed(wind_mean * climate_factor**0.5, wind_std)
                    center = simulate_hurricane_center()
                    loss, _ = calculate_loss(exposure_df, wind, center)
                    year_loss += loss
                losses.append(year_loss)

            fig, ax = plt.subplots(figsize=(10,6))
            sorted_l = sorted(losses, reverse=True)
            probs = np.arange(1, len(sorted_l)+1) / len(sorted_l)
            ax.loglog(sorted_l, probs, 'o', markersize=3, alpha=0.7, color="#d62728")
            ax.grid(True, which="both", ls="--")
            ax.set_xlabel("Annual Loss ($)")
            ax.set_ylabel("Exceedance Probability")
            ax.set_title("Loss Exceedance Curve")
            st.pyplot(fig)

with tab2:
    st.subheader("Animated Hurricane Track")
    if st.button("Launch Animated Storm"):
        wind = sample_wind_speed(wind_mean, wind_std)
        start_lat, start_lon = simulate_hurricane_center()
        track = []
        lat, lon = start_lat, start_lon
        for hour in range(15):
            lat += np.random.normal(0.03, 0.02)
            lon -= 0.12  # West-northwest track
            wind_reduced = max(60, wind - hour*4)
            track.append((lat, lon, wind_reduced))

        features = []
        for i, (lt, ln, w) in enumerate(track):
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [ln, lt]},
                "properties": {
                    "time": f"2025-09-01T{i:02d}:00:00",
                    "popup": f"Hour {i} — {w:.0f} mph",
                    "icon": "circle",
                    "iconstyle": {"color": "red" if w>100 else "orange"}
                }
            })

        m = folium.Map(location=[27.5, -83], zoom_start=7)
        TimestampedGeoJson(
            {"type": "FeatureCollection", "features": features},
            period="PT1H", add_last_point=True, auto_play=True, loop=False
        ).add_to(m)
        folium_static(m, width=800, height=500)

with tab3:
    st.subheader("3D Wind Speed Surface")
    if st.button("Generate 3D Wind Field"):
        wind = sample_wind_speed(wind_mean, wind_std)
        center = simulate_hurricane_center()
        x = np.linspace(center[1]-2, center[1]+2, 50)
        y = np.linspace(center[0]-2, center[0]+2, 50)
        X, Y = np.meshgrid(x, y)
        Z = wind * np.exp(-((X-center[1])**2 + (Y-center[0])**2)/1.5)

        fig = go.Figure(data=[go.Surface(z=Z, x=X, y=Y, colorscale='Reds')])
        fig.update_layout(title=f"3D Wind Field — Peak {wind:.0f} mph", scene=dict(
            xaxis_title='Longitude', yaxis_title='Latitude', zaxis_title='Wind Speed (mph)'))
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Damage Heatmap")
    if st.button("Generate Heatmap"):
        wind = sample_wind_speed(wind_mean, wind_std)
        center = simulate_hurricane_center()
        _, impacted = calculate_loss(exposure_df, wind, center)

        m = folium.Map(location=[27.8, -83], zoom_start=7, tiles="CartoDB positron")
        folium.Circle(location=center, radius=wind*900, color="red", fill_opacity=0.2).add_to(m)

        heat_data = [[lat, lon, dmg*100] for lat, lon, dmg in impacted]
        HeatMap(heat_data, radius=25, blur=20).add_to(m)

        folium_static(m, width=800, height=500)

# ——————— PDF REPORT EXPORT ———————
if st.button("Download PDF Report"):
    html = f"""
    <h1>Hurricane Risk Report — {climate_year}</h1>
    <p>Mean Annual Loss: ${np.mean(quick):,.0f}</p>
    <p>99% VaR: ${np.quantile(quick, 0.99):,.0f}</p>
    <p>Generated on {pd.Timestamp('today').strftime('%Y-%m-%d')}</p>
    """
    st.download_button("Download Report.pdf", html, file_name="hurricane_report.html")
