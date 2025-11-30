{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pandas as pd\
import numpy as np\
import matplotlib.pyplot as plt\
import folium\
from streamlit_folium import folium_static\
from models.loss_model import *\
\
st.set_page_config(page_title="Hurricane Risk Demo", layout="wide")\
st.title("\uc0\u55356 \u57130 \u65039  Interactive Florida Hurricane Risk Simulator")\
\
exposure_df = pd.read_csv("data/exposure.csv")\
\
# Sidebar controls\
st.sidebar.header("Change Hurricane Parameters")\
lambda_param = st.sidebar.slider("Avg hurricanes per year", 0.1, 5.0, 0.56, 0.1)\
wind_mean = st.sidebar.slider("Mean wind speed (mph)", 70, 160, 104)\
wind_std = st.sidebar.slider("Wind speed variation", 10, 50, 25)\
threshold = st.sidebar.slider("Damage threshold (mph)", 100, 200, 150)\
years = st.sidebar.slider("Simulation years", 1000, 100000, 20000)\
\
col1, col2 = st.columns(2)\
\
with col1:\
    if st.button("\uc0\u55358 \u56814  Run Full Loss Simulation"):\
        with st.spinner("Running thousands of years..."):\
            losses = []\
            for _ in range(years):\
                events = simulate_event_frequency(lambda_param)\
                year_loss = 0\
                for _ in range(events):\
                    wind = sample_wind_speed(wind_mean, wind_std)\
                    center = simulate_hurricane_center()\
                    loss, _ = calculate_loss(exposure_df, wind, center)\
                    year_loss += loss\
                losses.append(year_loss)\
\
            fig, ax = plt.subplots()\
            sorted_losses = sorted(losses, reverse=True)\
            probs = np.arange(1, len(sorted_losses)+1) / len(sorted_losses)\
            ax.loglog(sorted_losses, probs, 'o', markersize=3)\
            ax.grid(True, which="both")\
            ax.set_xlabel("Loss ($)")\
            ax.set_ylabel("Exceedance Probability")\
            ax.set_title("Loss Exceedance Curve")\
            st.pyplot(fig)\
\
            st.success(f"Mean annual loss: $\{np.mean(losses):,.0f\}")\
\
with col2:\
    st.subheader("\uc0\u55357 \u56826 \u65039  Simulate One Hurricane Right Now")\
    if st.button("Generate Storm"):\
        wind = sample_wind_speed(wind_mean, wind_std)\
        center = simulate_hurricane_center()\
        total_loss, impacted = calculate_loss(exposure_df, wind, center)\
\
        m = folium.Map(location=[27.8, -83], zoom_start=7)\
        folium.Circle(location=center, radius=wind*800, color="red", fill=True, opacity=0.3).add_to(m)\
        for lat, lon, dmg in impacted:\
            color = "red" if dmg > 0.6 else "orange" if dmg > 0 else "green"\
            folium.Marker([lat, lon], popup=f"Damage \{dmg:.0%\}", icon=folium.Icon(color=color)).add_to(m)\
\
        st.write(f"\uc0\u55356 \u57130 \u65039  Wind speed: \{wind:.0f\} mph | Total loss: $\{total_loss:,.0f\}")\
        folium_static(m, width=700, height=500)}