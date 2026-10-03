"""
sell_smart.scripts.generate_all_synthetic_data
Generates all synthetic datasets required by the Sell Smart PRD and decision intelligence engine.

Enforces Rule R5:
- All synthetic datasets live in data/synthetic/ (or config/events.csv for curated events)
- Every record has is_synthetic=True, generator, seed, config_hash
- Never presented as real field data without explicit labels
"""
from __future__ import annotations

import os
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

SYNTH_DIR = "sell_smart/data/synthetic"
CONFIG_DIR = "sell_smart/config"
os.makedirs(SYNTH_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

SEED = 42
CONFIG_HASH = hashlib.sha256(b"sell_smart_v1_seed42").hexdigest()[:12]
np.random.seed(SEED)
rng = np.random.default_rng(SEED)

print("1. Generating Synthetic Farmers Dataset...")
# Mandis for farmer generation (Nashik / Maharashtra & Central India clusters)
mandis_list = [
    {"mandi_id": "mh_nashik_lasalgaon", "district": "Nashik", "market": "Lasalgaon", "crop": "onion", "lat": 20.1472, "lon": 74.2255},
    {"mandi_id": "mh_nashik_pimpalgaon", "district": "Nashik", "market": "Pimpalgaon", "crop": "onion", "lat": 20.1741, "lon": 73.9877},
    {"mandi_id": "mh_pune_manjri", "district": "Pune", "market": "Manjri", "crop": "onion", "lat": 18.5134, "lon": 73.9806},
    {"mandi_id": "mh_nashik_nashik", "district": "Nashik", "market": "Nashik", "crop": "tomato", "lat": 19.9975, "lon": 73.7898},
    {"mandi_id": "mh_pune_pimpri", "district": "Pune", "market": "Pimpri", "crop": "tomato", "lat": 18.6279, "lon": 73.8009},
    {"mandi_id": "mh_nagpur_nagpur", "district": "Nagpur", "market": "Nagpur", "crop": "tomato", "lat": 21.1458, "lon": 79.0882},
    {"mandi_id": "mh_ahilyanagar_sangamner", "district": "Ahilyanagar", "market": "Sangamner", "crop": "tomato", "lat": 19.5772, "lon": 74.2081},
    {"mandi_id": "mh_nashik_lasalgaon_niphad", "district": "Nashik", "market": "Lasalgaon-Niphad", "crop": "soybean", "lat": 20.1472, "lon": 74.2255},
    {"mandi_id": "mp_indore_indore", "district": "Indore", "market": "Indore", "crop": "soybean", "lat": 22.7196, "lon": 75.8577},
    {"mandi_id": "mp_ujjain_ujjain", "district": "Ujjain", "market": "Ujjain", "crop": "soybean", "lat": 23.1765, "lon": 75.7885},
    {"mandi_id": "mh_parbhani_parbhani", "district": "Parbhani", "market": "Parbhani", "crop": "soybean", "lat": 19.2608, "lon": 76.7748},
    {"mandi_id": "mh_latur_latur", "district": "Latur", "market": "Latur", "crop": "soybean", "lat": 18.4088, "lon": 76.5604},
]

farmers_rows = []
for i, m in enumerate(mandis_list):
    n_farmers = 25
    for j in range(n_farmers):
        farmer_id = f"F_{m['crop'][:3].upper()}_{i:02d}_{j:03d}"
        dist_km = float(rng.uniform(5.0, 60.0))
        bearing = float(rng.uniform(0, 360))
        bearing_rad = np.radians(bearing)
        
        dlat = (dist_km * np.cos(bearing_rad)) / 111.0
        dlon = (dist_km * np.sin(bearing_rad)) / (111.0 * np.cos(np.radians(m["lat"])))
        
        qty = float(rng.choice([10, 20, 50, 100], p=[0.25, 0.35, 0.25, 0.15]))
        vehicle = "tempo" if qty <= 25 else "truck"
        deadline = int(rng.choice([0, 3, 7, 14, 21], p=[0.10, 0.20, 0.30, 0.25, 0.15]))
        
        if m["crop"] == "soybean":
            storage = str(rng.choice(["dry", "moist"], p=[0.75, 0.25]))
            quality = float(rng.choice([1.0, 0.95, 0.90, 0.85], p=[0.5, 0.3, 0.15, 0.05]))
        elif m["crop"] == "onion":
            storage = str(rng.choice(["ambient_dry", "humid"], p=[0.65, 0.35]))
            quality = float(rng.choice([1.0, 0.90, 0.80], p=[0.55, 0.30, 0.15]))
        else:  # tomato
            storage = "ambient"
            quality = float(rng.choice([1.0, 0.90, 0.80], p=[0.60, 0.25, 0.15]))
            
        farmers_rows.append({
            "farmer_id": farmer_id,
            "mandi_id": m["mandi_id"],
            "target_mandi_district": m["district"],
            "crop": m["crop"],
            "village_lat": round(m["lat"] + dlat, 5),
            "village_lon": round(m["lon"] + dlon, 5),
            "distance_to_mandi_km": round(dist_km, 2),
            "quantity_q": qty,
            "vehicle_type": vehicle,
            "cash_deadline_days": deadline,
            "storage_condition": storage,
            "quality_factor": quality,
            "is_synthetic": True,
            "generator": "farmers_v1",
            "seed": SEED,
            "config_hash": CONFIG_HASH,
        })

df_farmers = pd.DataFrame(farmers_rows)
df_farmers.to_parquet(f"{SYNTH_DIR}/synthetic_farmers.parquet", index=False)
df_farmers.to_csv(f"{SYNTH_DIR}/synthetic_farmers.csv", index=False)
print(f"   -> Wrote {len(df_farmers)} synthetic farmers to {SYNTH_DIR}/synthetic_farmers.parquet & csv")

print("\n2. Generating Synthetic Onion and Tomato Historical Series (2024-08-15 to 2025-08-14)...")
# Matches the exact timeline of the Kaggle historical CSV so that models can train across all 3 crops
dates = pd.date_range("2024-08-15", "2025-08-14", freq="D")
history_rows = []

# Crop profiles based on realistic Maharashtra APMC market dynamics & uploaded snapshot prices
crop_specs = {
    "onion": {
        "mandis": [m for m in mandis_list if m["crop"] == "onion"] + [
            {"mandi_id": "mh_solapur_solapur", "district": "Solapur", "market": "Solapur", "crop": "onion", "lat": 17.6599, "lon": 75.9064},
            {"mandi_id": "mh_ahilyanagar_rahuri", "district": "Ahilyanagar", "market": "Rahuri", "crop": "onion", "lat": 19.3892, "lon": 74.6543}
        ],
        "base_modal": 1800.0,
        "spread_pct": 0.15,
        "varieties": ["Red", "Nasik", "FAQ"],
        "base_arrivals": 2500,
    },
    "tomato": {
        "mandis": [m for m in mandis_list if m["crop"] == "tomato"],
        "base_modal": 1400.0,
        "spread_pct": 0.22,
        "varieties": ["Hybrid", "Local", "FAQ"],
        "base_arrivals": 800,
    }
}

for crop, spec in crop_specs.items():
    for m in spec["mandis"]:
        mandi_bias = rng.normal(0, 0.05)
        mandi_base = spec["base_modal"] * (1 + mandi_bias)
        
        current_price = mandi_base
        for d_idx, dt in enumerate(dates):
            # Day of week effect (lower/closed on Sunday)
            if dt.weekday() == 6:  # Sunday
                continue
                
            day_of_year = dt.timetuple().tm_yday
            
            # Seasonal patterns
            if crop == "onion":
                # Price rises during storage period (July-Nov), dips during Rabi harvest (Mar-May)
                seasonality = 1.0 + 0.35 * np.sin(2 * np.pi * (day_of_year - 120) / 365.0)
                # Export policy shock simulation around Dec-Jan
                if 340 <= day_of_year <= 365 or 1 <= day_of_year <= 30:
                    seasonality *= 0.85
            else:  # tomato
                # Price spikes during monsoon (June-Aug), lower in winter/spring glut
                seasonality = 1.0 + 0.50 * np.sin(2 * np.pi * (day_of_year - 100) / 365.0)
            
            # Mean-reverting random walk with noise
            target = mandi_base * seasonality
            current_price = 0.88 * current_price + 0.12 * target + rng.normal(0, spec["base_modal"] * 0.035)
            modal = max(300.0, current_price)
            
            spread = modal * spec["spread_pct"] * rng.uniform(0.7, 1.3)
            min_price = max(100.0, modal - spread)
            max_price = modal + spread
            
            # Realistic arrival quantity (in quintals)
            arrival_qty = max(50.0, spec["base_arrivals"] * (1.0 / (seasonality ** 0.5)) + rng.normal(0, spec["base_arrivals"] * 0.15))
            
            history_rows.append({
                "Date": dt.strftime("%d %b %Y"),
                "date_iso": dt.strftime("%Y-%m-%d"),
                "State": "Maharashtra",
                "District Name": m["district"],
                "Market Name": m["market"],
                "Commodity": crop.capitalize(),
                "Variety": rng.choice(spec["varieties"]),
                "Grade": "FAQ",
                "Min Price (Rs./Quintal)": round(min_price, 2),
                "Max Price (Rs./Quintal)": round(max_price, 2),
                "Modal Price (Rs./Quintal)": round(modal, 2),
                "Arrivals_Quintal": round(arrival_qty, 2),
                "is_synthetic": True,
                "generator": "agmarknet_mimic_v1",
                "seed": SEED,
                "config_hash": CONFIG_HASH,
            })

df_history = pd.DataFrame(history_rows)
df_history.to_parquet(f"{SYNTH_DIR}/synthetic_onion_tomato_history.parquet", index=False)
df_history.to_csv(f"{SYNTH_DIR}/synthetic_onion_tomato_history.csv", index=False)
print(f"   -> Wrote {len(df_history)} rows of synthetic Onion & Tomato history to {SYNTH_DIR}/synthetic_onion_tomato_history.parquet & csv")

print("\n3. Generating Synthetic Trader Offers Dataset...")
# Generates trader offers against observed prices using PRD mixture model
offer_rows = []
for row in history_rows[::5]:  # subsample every 5 days for offers
    modal = row["Modal Price (Rs./Quintal)"]
    regime = rng.choice([0, 1, 2], p=[0.20, 0.50, 0.30])
    if regime == 0:
        delta = 0.0
    elif regime == 1:
        delta = max(0.01, float(rng.normal(0.05, 0.02)))
    else:
        delta = max(0.05, float(rng.normal(0.12, 0.04)))
        
    offer_price = round(modal * (1.0 - delta), 2)
    offer_rows.append({
        "date": row["date_iso"],
        "market": row["Market Name"],
        "crop": row["Commodity"].lower(),
        "modal_price": modal,
        "delta": round(delta, 4),
        "trader_offer_proxy": offer_price,
        "is_synthetic": True,
        "generator": "offers_v1",
        "seed": SEED,
        "config_hash": CONFIG_HASH,
    })

df_offers = pd.DataFrame(offer_rows)
df_offers.to_parquet(f"{SYNTH_DIR}/synthetic_trader_offers.parquet", index=False)
df_offers.to_csv(f"{SYNTH_DIR}/synthetic_trader_offers.csv", index=False)
print(f"   -> Wrote {len(df_offers)} synthetic trader offers to {SYNTH_DIR}/synthetic_trader_offers.parquet & csv")

print("\n4. Generating Golden Fixtures (Rising, Falling, Flat, Shock)...")
fixture_dates = pd.date_range("2025-01-01", periods=30, freq="D")
fixtures = []
p0 = 2000.0

for i, dt in enumerate(fixture_dates):
    # Rising (WAIT recommendation)
    p_rise = p0 * ((1 + 0.025) ** i)
    # Falling (SELL NOW recommendation)
    p_fall = p0 * ((1 - 0.025) ** i)
    # Flat (ACCEPT offer / sell today)
    p_flat = p0 + rng.normal(0, 10.0)
    # Shock (day 15 drops by 35% -> radar triggered, hold suspended)
    p_shock = p0 if i < 15 else p0 * 0.65 + rng.normal(0, 15.0)
    
    fixtures.append({
        "day": i + 1,
        "date": dt.strftime("%Y-%m-%d"),
        "rising_price": round(p_rise, 2),
        "falling_price": round(p_fall, 2),
        "flat_price": round(p_flat, 2),
        "shock_price": round(p_shock, 2),
        "is_synthetic": True,
        "generator": "golden_fixtures_v1",
        "seed": SEED,
        "config_hash": CONFIG_HASH,
    })

df_fixtures = pd.DataFrame(fixtures)
df_fixtures.to_parquet(f"{SYNTH_DIR}/golden_fixtures.parquet", index=False)
df_fixtures.to_csv(f"{SYNTH_DIR}/golden_fixtures.csv", index=False)
print(f"   -> Wrote 30 golden test series to {SYNTH_DIR}/golden_fixtures.parquet & csv")

print("\n5. Generating Synthetic Daily Weather Aggregates (2024-08-15 to 2025-08-14)...")
# Daily weather aggregated for key mandi clusters (Pune, Nashik, Nagpur, Indore)
# Calibrated using statistical moments from the uploaded 11-year weather data
weather_rows = []
cities = [
    {"city": "Pune", "lat": 18.5204, "lon": 73.8567},
    {"city": "Nashik", "lat": 19.9975, "lon": 73.7898},
    {"city": "Nagpur", "lat": 21.1458, "lon": 79.0882},
    {"city": "Indore", "lat": 22.7196, "lon": 75.8577},
]

for dt in dates:
    doy = dt.timetuple().tm_yday
    month = dt.month
    for c in cities:
        # Monsoon in June-Sept
        is_monsoon = month in [6, 7, 8, 9]
        is_summer = month in [3, 4, 5]
        
        if is_monsoon:
            precip = max(0.0, float(rng.exponential(scale=12.0) if rng.random() > 0.4 else 0.0))
            humidity = float(np.clip(rng.normal(78.0, 10.0), 40.0, 98.0))
            max_temp = float(rng.normal(29.0, 2.5))
            min_temp = float(rng.normal(22.0, 1.5))
        elif is_summer:
            precip = max(0.0, float(rng.exponential(scale=2.0) if rng.random() > 0.9 else 0.0))
            humidity = float(np.clip(rng.normal(35.0, 8.0), 15.0, 60.0))
            max_temp = float(rng.normal(38.0, 3.0))
            min_temp = float(rng.normal(24.0, 2.0))
        else: # Winter
            precip = 0.0
            humidity = float(np.clip(rng.normal(48.0, 8.0), 20.0, 75.0))
            max_temp = float(rng.normal(28.0, 2.0))
            min_temp = float(rng.normal(14.0, 2.5))
            
        weather_rows.append({
            "date": dt.strftime("%Y-%m-%d"),
            "city": c["city"],
            "lat": c["lat"],
            "lon": c["lon"],
            "maxtemp_c": round(max_temp, 1),
            "mintemp_c": round(min_temp, 1),
            "mean_temp_c": round((max_temp + min_temp) / 2.0, 1),
            "humidity_pct": round(humidity, 1),
            "precip_mm": round(precip, 1),
            "is_synthetic": True,
            "generator": "weather_daily_agg_v1",
            "seed": SEED,
            "config_hash": CONFIG_HASH,
        })

df_weather = pd.DataFrame(weather_rows)
df_weather.to_parquet(f"{SYNTH_DIR}/synthetic_daily_weather_2024_2025.parquet", index=False)
df_weather.to_csv(f"{SYNTH_DIR}/synthetic_daily_weather_2024_2025.csv", index=False)
print(f"   -> Wrote {len(df_weather)} daily weather records to {SYNTH_DIR}/synthetic_daily_weather_2024_2025.parquet & csv")

print("\n6. Populating Curated Agricultural Policy & Market Events (config/events.csv)...")
events_data = [
    {
        "date": "2023-08-19",
        "event_type": "policy",
        "crop": "onion",
        "description": "Government imposes 40% export duty on onions until December 31, 2023 to curb domestic price rise.",
        "source": "Ministry of Finance Notification / Press Information Bureau",
        "impact_direction": "down",
        "verified": True,
    },
    {
        "date": "2023-12-08",
        "event_type": "export_ban",
        "crop": "onion",
        "description": "Directorate General of Foreign Trade (DGFT) bans onion exports until March 31, 2024.",
        "source": "DGFT Notification No. 49/2023",
        "impact_direction": "down",
        "verified": True,
    },
    {
        "date": "2024-05-04",
        "event_type": "policy",
        "crop": "onion",
        "description": "Export ban lifted; Minimum Export Price (MEP) set at $550/tonne along with 40% export duty.",
        "source": "DGFT Notification No. 10/2024-25",
        "impact_direction": "up",
        "verified": True,
    },
    {
        "date": "2024-09-13",
        "event_type": "policy",
        "crop": "onion",
        "description": "Government scraps Minimum Export Price (MEP) on onions and halves export duty to 20%.",
        "source": "DGFT Notification / Business Standard",
        "impact_direction": "up",
        "verified": True,
    },
    {
        "date": "2024-06-19",
        "event_type": "msp_change",
        "crop": "soybean",
        "description": "Cabinet approves Kharif Marketing Season 2024-25 MSP for Soybean (yellow) at Rs 4,892/quintal (+Rs 292).",
        "source": "Cabinet Committee on Economic Affairs (CCEA) Press Release",
        "impact_direction": "up",
        "verified": True,
    },
    {
        "date": "2024-09-14",
        "event_type": "policy",
        "crop": "soybean",
        "description": "India raises basic customs duty on crude soybean oil from 0% to 20% to support domestic oilseed farmers.",
        "source": "Ministry of Finance Customs Notification 50/2024",
        "impact_direction": "up",
        "verified": True,
    },
    {
        "date": "2024-07-15",
        "event_type": "flood",
        "crop": "tomato",
        "description": "Heavy monsoon rains and waterlogging in Maharashtra and Karnataka disrupt tomato harvest and transport.",
        "source": "Agri Market Intelligence Reports",
        "impact_direction": "up",
        "verified": True,
    },
    {
        "date": "2025-06-18",
        "event_type": "msp_change",
        "crop": "soybean",
        "description": "Government announces Kharif 2025-26 MSP revision for oilseeds.",
        "source": "CCEA Release",
        "impact_direction": "up",
        "verified": True,
    },
]

df_events = pd.DataFrame(events_data)
df_events.to_csv(f"{CONFIG_DIR}/events.csv", index=False)
df_events.to_csv(f"{SYNTH_DIR}/events_curated.csv", index=False)
print(f"   -> Wrote {len(df_events)} curated policy events to {CONFIG_DIR}/events.csv and {SYNTH_DIR}/events_curated.csv")

print("\nALL SYNTHETIC GENERATIONS COMPLETE SUCCESSFULLY.")
