import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
from models.loss_model import *

st.set_page_config(page_title="Florida Hurricane Risk", layout="wide")
st.title("🌪️ Florida Hurricane Risk Simulator")
st.markdown("**Adjust the sliders → click the buttons → watch the map & losses update instantly!**")

# Load data
exposure_df = pd.read_csv("data/exposure.csv")

# Sidebar
st.sidebar.header("Hurricane Settings")
lambda_param = st.sidebar.slider("Average hurricanes per year", 0.1, 5.0, 0.56, 0.05)
wind_mean = st.sidebar.slider("Mean wind speed (mph)", 70, 160, 104)
wind_std = st.sidebar.slider("Wind speed variation (mph)", 10, 50, 25)
threshold = st.sidebar.slider("Damage threshold (mph)", 100, 200, 150)
years = st.sidebar.slider("Simulation years", 1000, 100000, 20000, step=1000)

col1, col2 = st.columns(2)

# LEFT: Full simulation + loss curve
with col1:
    st.subheader("🧮 Full Loss Simulation")
    if st.button("Run 20,000+ years of hurricanes", type="primary"):
        with st.spinner("Simulating thousands of years..."):
            losses = []
            for _ in range(years):
                events = simulate_event_frequency(lambda_param)
                year_loss = 0
                for _ in range(events):
                    wind = sample_wind_speed(wind_mean, wind_std)
                    center = simulate_hurricane_center()
                    loss, _ = calculate_loss(exposure_df, wind, center)
                    year_loss += loss
                losses.append(year_loss)

            fig, ax = plt.subplots(figsize=(9,6))
            sorted_losses = sorted(losses, reverse=True)
            probs = np.arange(1, len(sorted_losses)+1) / len(sorted_losses)
            ax.loglog(sorted_losses, probs, 'o', markersize=4, alpha=0.6)
            ax.grid(True, which="both", ls="--")
            ax.set_xlabel("Loss ($)")
            ax.set_ylabel("Exceedance Probability")
            ax.set_title("Loss Exceedance Curve")
            st.pyplot(fig)

            st.success(f"**Mean annual loss:** ${np.mean(losses):,.0f}  |  **99th percentile:** ${np.quantile(losses, 0.99):,.0f}")

# RIGHT: Single storm + live map
with col2:
    st.subheader("🗺️ Generate One Hurricane Right Now")
    if st.button("Create Storm", type="primary"):
        wind = sample_wind_speed(wind_mean, wind_std)
        center = simulate_hurricane_center()
        total_loss, impacted = calculate_loss(exposure_df, wind, center)

        m = folium.Map(location=[27.8, -83], zoom_start=7, tiles="CartoDB positron")
        folium.Circle(location=center,
                      radius=wind*900,
                      color="crimson",
                      weight=2,
                      fill=True,
                      fill_opacity=0.25,
                      tooltip=f"{wind:.0f} mph").add_to(m)

        for lat, lon, dmg in impacted:
            color = "darkred" if dmg > 0.7 else "orange" if dmg > 0.3 else "green"
            folium.CircleMarker([lat, lon],
                                radius=10,
                                color=color,
                                fill=True,
                                popup=f"Damage: {dmg:.0%}<br>Value: ${exposure_df.loc[(exposure_df.lat==lat)&(exposure_df.lon==lon), 'insured_value'].values[0]:,}",
                                tooltip=f"{dmg:.0%} damage").add_to(m)

        st.write(f"**Wind speed:** {wind:.0f} mph  |  **Total loss this storm:** ${total_loss:,.0f}")
        folium_static(m, width=720, height=560)