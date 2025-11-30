{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import numpy as np\
from scipy.stats import poisson, norm\
\
def simulate_event_frequency(lambda_param=0.56):\
    return poisson.rvs(mu=lambda_param)\
\
def sample_wind_speed(mean=104, std=25):\
    return max(74, norm.rvs(loc=mean, scale=std))\
\
def vulnerability_function(wind_speed, threshold=150):\
    return min(1.0, max(0.0, wind_speed / threshold))\
\
def calculate_loss(exposure_df, wind_speed, hurricane_center):\
    damage_ratio = vulnerability_function(wind_speed)\
    radius_km = wind_speed * 0.5\
    losses = []\
    impacted = []\
    for _, row in exposure_df.iterrows():\
        dist = np.sqrt((row['lat'] - hurricane_center[0])**2 + (row['lon'] - hurricane_center[1])**2) * 111\
        if dist <= radius_km:\
            loss = row['insured_value'] * damage_ratio\
            losses.append(loss)\
            impacted.append((row['lat'], row['lon'], damage_ratio))\
        else:\
            losses.append(0)\
            impacted.append((row['lat'], row['lon'], 0))\
    return sum(losses), impacted\
\
def simulate_hurricane_center():\
    return (np.random.uniform(24.5, 30.5), np.random.uniform(-87.5, -80.0))}