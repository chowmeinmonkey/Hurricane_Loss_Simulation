import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
from scipy.stats import poisson, norm


# Built-in exposure data (5 properties in Florida)
data = {
    "property_id": [1, 2, 3, 4, 5],
    "insured_value": [500000, 750000, 1000000, 600000, 800000],
    "location_id": ["Miami", "Tampa", "Tallahassee", "Orlando", "Fort Lauderdale"],
    "construction_type": ["wood", "brick", "concrete", "wood", "brick"],
    "lat": [25.7617, 27.9478, 30.4383, 28.5383, 26.1224],
    "lon": [-80.1918, -82.4584, -84.2807, -81.3792, -80.1373]
}
exposure_df = pd.DataFrame(data)

# Model functions
def simulate_event_frequency(lambda_param=0.56):
    return poisson.rvs(mu=lambda_param)

def sample_wind_speed(mean=104, std=25):
    return max(74, norm.rvs(loc=mean, scale=std))

def vulnerability_function(wind_speed, threshold=150):
    return min(1.0, max(0.0, wind_speed / threshold))

def calculate_loss(df, wind_speed, center):
    damage_ratio = vulnerability_function(wind_speed)
    radius_km = wind_speed * 0.5
    losses = []
    impacted = []
    for _, row in df.iterrows():
        dist = np.sqrt((row['lat'] - center[0])**2 + (row['lon'] - center[1])**2) * 111
        if dist <= radius_km:
            loss = row['insured_value'] * damage_ratio
            losses.append(loss)
            impacted.append((row['lat'], row['lon'], damage_ratio))
        else:
            losses.append(0)
            impacted.append((row['lat'], row['lon'], 0))
    return sum(losses), impacted

def simulate_hurricane_center():
    return (np.random.uniform(24.5, 30.5), np.random.uniform(-87.5, -80.0))

# ———————————————— STREAMLIT APP ————————————————

st.set_page_config(page_title="Florida Hurricane Risk", layout="wide")
st.title("Florida Hurricane Risk Simulator")

st.sidebar.header("Hurricane Settings")
lambda_param = st.sidebar.slider("Average hurricanes/year", 0.1, 5.0, 0.56, 0.05)
wind_mean    = st.sidebar.slider("Mean wind speed (mph)", 70, 160, 104)
wind_std     = st.sidebar.slider("Wind variation (mph)", 10, 50, 25)
threshold    = st.sidebar.slider("Damage threshold (mph)", 100, 200, 150)
years        = st.sidebar.slider("Simulation years", 1000, 100000, 20000, 1000)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Full Loss Simulation")
    if st.button("Run simulation", type="primary"):
        with st.spinner("Running Monte-Carlo…"):
            annual_losses = []
            for _ in range(years):
                events = simulate_event_frequency(lambda_param)
                year_loss = 0
                for _ in range(events):
                    wind = sample_wind_speed(wind_mean, wind_std)
                    center = simulate_hurricane_center()
                    loss, _ = calculate_loss(exposure_df, wind, center)
                    year_loss += loss
                annual_losses.append(year_loss)

            fig, ax = plt.subplots(figsize=(9,6))
            sorted_losses = sorted(annual_losses, reverse=True)
            probs = np.arange(1, len(sorted_losses)+1) / len(sorted_losses)
            ax.loglog(sorted_losses, probs, 'o', markersize=4, alpha=0.7, color="#d62728")
            ax.grid(True, which="both", ls="--", alpha=0.5)
            ax.set_xlabel("Loss ($)")
            ax.set_ylabel("Exceedance Probability")
            ax.set_title("Loss Exceedance Curve")
            st.pyplot(fig)
            st.success(f"Mean annual loss: ${np.mean(annual_losses):,.0f}")

with col2:
    st.subheader("Generate One Hurricane")
    if st.button("Create Storm", type="primary"):
        wind = sample_wind_speed(wind_mean, wind_std)
        center = simulate_hurricane_center()
        total_loss, impacted = calculate_loss(exposure_df, wind, center)

        m = folium.Map(location=[27.8, -83], zoom_start=7, tiles="CartoDB positron")
        folium.Circle(location=center, radius=wind*900, color="crimson", weight=2,
                      fill=True, fill_opacity=0.25, tooltip=f"{wind:.0f} mph").add_to(m)

        for lat, lon, dmg in impacted:
            color = "darkred" if dmg > 0.7 else "orange" if dmg > 0.3 else "green"
            folium.CircleMarker([lat, lon], radius=10, color=color, fill=True,
                                tooltip=f"{dmg:.0%} damage").add_to(m)

        st.write(f"Wind: {wind:.0f} mph  |  Loss: ${total_loss:,.0f}")
        folium_static(m, width=720, height=560)