"""
sell_smart.ingest.climate_factors
Ingestor for the climate-change agriculture factors dataset.

Schema (input CSV):
  Temperature            - int (degrees C)
  Precipitation          - int (mm or index)
  CO2 Levels             - int (ppm)
  Crop Yield             - int (kg/ha proxy)
  Soil Health            - int (1-10 scale)
  Extreme Weather Events - str (Drought | Heatwave | Flood | Storm)
  Crop Disease Incidence - str (Low | Medium | High)
  Water Availability     - str (Low | Medium | High)
  Food Security          - str (Low | Medium | High)
  Economic Impact        - str (Low | Medium | High)

No date or mandi column exists. This dataset represents climate risk scenarios,
not a time series. It is used to:
  1. Derive regional climate statistics (mean temperature, precipitation) that
     activate the dormant weather_temp_mean / weather_rain_7d feature slots.
  2. Build a climate_stress_index (0-1) from numeric + categorical risk factors.
  3. Encode extreme weather types as shock priors for the shock radar.
  4. Adjust economics confidence via disease incidence + water availability.

Source: ML/climate_change_agriculture_dataset.csv
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from sellsmart.ingest.base import Ingestor
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

# Ordinal encoding maps (Low < Medium < High)
ORDINAL_MAP = {"Low": 0, "Medium": 1, "High": 2}
WEATHER_EVENT_MAP = {"Drought": 0, "Storm": 1, "Flood": 2, "Heatwave": 3}

# Column renaming for clean internal names
_RENAME = {
    "Temperature": "temperature_c",
    "Precipitation": "precipitation_mm",
    "CO2 Levels": "co2_ppm",
    "Crop Yield": "crop_yield_proxy",
    "Soil Health": "soil_health_score",
    "Extreme Weather Events": "extreme_weather_type",
    "Crop Disease Incidence": "disease_incidence",
    "Water Availability": "water_availability",
    "Food Security": "food_security",
    "Economic Impact": "economic_impact",
}


class ClimateFactorsIngestor(Ingestor):
    """Ingest the climate change agriculture factors CSV into bronze parquet."""

    source_name = "climate_change_agriculture_factors"

    def __init__(self, csv_path: Path | str):
        self.csv_path = Path(csv_path)

    def ingest(self, output_dir: Path) -> pd.DataFrame:
        if not self.csv_path.exists():
            logger.warning(f"Climate factors CSV not found: {self.csv_path}. Skipping.")
            return pd.DataFrame()

        df = pd.read_csv(self.csv_path)
        logger.info(f"Climate factors: loaded {len(df):,} rows from {self.csv_path}")

        # Validate expected columns
        missing = set(_RENAME.keys()) - set(df.columns)
        if missing:
            raise ValueError(f"Climate factors CSV missing expected columns: {missing}")

        df = df.rename(columns=_RENAME)
        df["source"] = self.source_name
        df["ingested_at"] = datetime.now(timezone.utc).isoformat()
        df["row_id"] = range(len(df))  # synthetic row ID (no natural key)
        df["is_synthetic"] = False

        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "climate_factors_bronze.parquet"
        df.to_parquet(out_path, index=False)
        logger.info(f"Climate factors bronze: {len(df):,} rows -> {out_path}")
        return df

    def validate_schema(self, df: pd.DataFrame) -> None:
        required = set(_RENAME.values())
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Climate bronze schema missing: {missing}")


def encode_climate_silver(df_bronze: pd.DataFrame) -> pd.DataFrame:
    """
    Encode categoricals and derive risk scores from bronze climate data.

    Produces:
      - extreme_weather_type_enc  : int  (0=Drought, 1=Storm, 2=Flood, 3=Heatwave)
      - disease_incidence_enc     : int  (0=Low, 1=Medium, 2=High)
      - water_availability_enc    : int  (0=Low, 1=Medium, 2=High)
      - food_security_enc         : int  (0=Low, 1=Medium, 2=High)
      - economic_impact_enc       : int  (0=Low, 1=Medium, 2=High)
      - climate_stress_index      : float [0, 1]  composite risk score
      - is_extreme_event          : bool  True for Flood/Drought/Heatwave (not Storm)
    """
    df = df_bronze.copy()

    # Ordinal encoding
    for col, enc_col in [
        ("extreme_weather_type", "extreme_weather_type_enc"),
        ("disease_incidence", "disease_incidence_enc"),
        ("water_availability", "water_availability_enc"),
        ("food_security", "food_security_enc"),
        ("economic_impact", "economic_impact_enc"),
    ]:
        if col == "extreme_weather_type":
            df[enc_col] = df[col].map(WEATHER_EVENT_MAP).fillna(-1).astype(int)
        else:
            df[enc_col] = df[col].map(ORDINAL_MAP).fillna(-1).astype(int)

    # Normalise numeric columns to [0, 1] using known ranges
    temp_norm = df["temperature_c"].clip(0, 50) / 50.0                     # 0=cold, 1=hot
    precip_norm = df["precipitation_mm"].clip(0, 100) / 100.0              # 0=dry, 1=wet
    co2_norm = (df["co2_ppm"].clip(300, 500) - 300) / 200.0               # 0=300ppm, 1=500ppm
    soil_norm = 1.0 - ((df["soil_health_score"].clip(1, 10) - 1) / 9.0)   # inverted: low health = high stress
    yield_norm = 1.0 - (df["crop_yield_proxy"].clip(100, 1000) - 100) / 900.0  # inverted: low yield = high stress
    disease_stress = df["disease_incidence_enc"].clip(0, 2) / 2.0
    water_stress = 1.0 - (df["water_availability_enc"].clip(0, 2) / 2.0)  # inverted: low water = high stress
    econ_stress = 1.0 - (df["economic_impact_enc"].clip(0, 2) / 2.0)      # inverted: low econ impact = high stress

    # Extreme weather contributes hard stress
    extreme_stress = df["extreme_weather_type"].isin(["Drought", "Flood", "Heatwave"]).astype(float)

    # Weighted composite stress index
    df["climate_stress_index"] = (
        0.15 * temp_norm
        + 0.10 * precip_norm
        + 0.10 * co2_norm
        + 0.15 * soil_norm
        + 0.10 * yield_norm
        + 0.15 * disease_stress
        + 0.15 * water_stress
        + 0.10 * extreme_stress
    ).round(4)

    df["is_extreme_event"] = df["extreme_weather_type"].isin(["Drought", "Flood", "Heatwave"])

    return df


def compute_climate_summary(df_silver: pd.DataFrame) -> dict:
    """
    Compute aggregate statistics from the silver climate dataset.
    These are used as feature values broadcast across all (mandi, crop, date) rows
    since the climate dataset has no spatial/temporal keys.

    Returns a dict with:
        mean_temperature_c, std_temperature_c
        mean_precipitation_mm
        mean_co2_ppm
        mean_climate_stress_index
        extreme_event_rate        : fraction of rows with is_extreme_event=True
        high_disease_rate         : fraction of rows with disease_incidence=High
        low_water_rate            : fraction of rows with water_availability=Low
        shock_prior_probability   : P(extreme event) from dataset
        dominant_weather_event    : most frequent Extreme Weather Events category
    """
    if df_silver.empty:
        return {}

    summary = {
        "mean_temperature_c": round(float(df_silver["temperature_c"].mean()), 2),
        "std_temperature_c": round(float(df_silver["temperature_c"].std()), 2),
        "mean_precipitation_mm": round(float(df_silver["precipitation_mm"].mean()), 2),
        "mean_co2_ppm": round(float(df_silver["co2_ppm"].mean()), 2),
        "mean_soil_health": round(float(df_silver["soil_health_score"].mean()), 2),
        "mean_crop_yield_proxy": round(float(df_silver["crop_yield_proxy"].mean()), 2),
        "mean_climate_stress_index": round(float(df_silver["climate_stress_index"].mean()), 4),
        "p95_climate_stress_index": round(float(df_silver["climate_stress_index"].quantile(0.95)), 4),
        "extreme_event_rate": round(float(df_silver["is_extreme_event"].mean()), 4),
        "high_disease_rate": round(float((df_silver["disease_incidence"] == "High").mean()), 4),
        "low_water_rate": round(float((df_silver["water_availability"] == "Low").mean()), 4),
        "shock_prior_probability": round(float(df_silver["is_extreme_event"].mean()), 4),
        "dominant_weather_event": str(df_silver["extreme_weather_type"].mode().iloc[0]),
        "n_scenarios": int(len(df_silver)),
    }
    return summary
