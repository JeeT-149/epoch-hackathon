"""
sell_smart.tests.unit.test_climate_factors
Unit tests for:
  1. Climate factors ingestion, silver encoding, and scenario summary (as offline risk data)
  2. PRD 4.6 weather feature policy (disabled when use_weather=False, merged when use_weather=True)
  3. PRD 11 Policy-Shock Radar (S1-S5 signals, z=3.0, and multi-signal state evaluation)
"""
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

from sellsmart.ingest.climate_factors import (
    ClimateFactorsIngestor,
    encode_climate_silver,
    compute_climate_summary,
)
from sellsmart.features.build import build_features
from sellsmart.decision.confidence import compute_confidence
from sellsmart.shock.radar import detect_shocks, evaluate_radar_state, RadarLevel


@pytest.fixture
def sample_climate_df():
    return pd.DataFrame({
        "Temperature": [25, 42, 18, 35],
        "Precipitation": [50, 5, 80, 20],
        "CO2 Levels": [400, 480, 350, 420],
        "Crop Yield": [600, 250, 800, 450],
        "Soil Health": [7, 3, 8, 4],
        "Extreme Weather Events": ["Drought", "Heatwave", "Storm", "Flood"],
        "Crop Disease Incidence": ["Low", "High", "Low", "Medium"],
        "Water Availability": ["Medium", "Low", "High", "Low"],
        "Food Security": ["Medium", "Low", "High", "Medium"],
        "Economic Impact": ["Low", "High", "Low", "Medium"],
    })


@pytest.fixture
def sample_gold_panel():
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "mandi_id": ["mandi_1"] * 60,
        "crop": ["soybean"] * 60,
        "date": dates,
        "modal_price": [2000.0 + i * 5 for i in range(60)],
        "min_price": [1900.0 + i * 5 for i in range(60)],
        "max_price": [2100.0 + i * 5 for i in range(60)],
        "arrivals_qt": [100.0] * 60,
        "is_imputed": [False] * 60,
        "days_since_observed": [0] * 60,
    })
    return df


class TestClimateIngestion:
    def test_ingest_from_csv(self, tmp_path, sample_climate_df):
        csv_file = tmp_path / "climate_test.csv"
        sample_climate_df.to_csv(csv_file, index=False)
        
        ingestor = ClimateFactorsIngestor(csv_path=csv_file)
        bronze_dir = tmp_path / "bronze"
        bronze_df = ingestor.ingest(output_dir=bronze_dir)

        assert not bronze_df.empty
        assert len(bronze_df) == 4
        assert "temperature_c" in bronze_df.columns
        assert "precipitation_mm" in bronze_df.columns
        assert "extreme_weather_type" in bronze_df.columns
        assert (bronze_dir / "climate_factors_bronze.parquet").exists()

    def test_missing_file_returns_empty(self, tmp_path):
        ingestor = ClimateFactorsIngestor(csv_path=tmp_path / "non_existent.csv")
        df = ingestor.ingest(output_dir=tmp_path)
        assert df.empty


class TestClimateEncoding:
    def test_encode_silver(self, sample_climate_df, tmp_path):
        csv_file = tmp_path / "climate_test.csv"
        sample_climate_df.to_csv(csv_file, index=False)
        ingestor = ClimateFactorsIngestor(csv_path=csv_file)
        bronze_df = ingestor.ingest(output_dir=tmp_path)

        silver_df = encode_climate_silver(bronze_df)
        assert len(silver_df) == 4
        assert "extreme_weather_type_enc" in silver_df.columns
        assert "climate_stress_index" in silver_df.columns

        # Verify stress index is in [0, 1]
        assert (silver_df["climate_stress_index"] >= 0.0).all()
        assert (silver_df["climate_stress_index"] <= 1.0).all()
        assert bool(silver_df.loc[silver_df["extreme_weather_type"] == "Drought", "is_extreme_event"].iloc[0]) is True


class TestClimateSummary:
    def test_compute_summary(self, sample_climate_df, tmp_path):
        csv_file = tmp_path / "climate_test.csv"
        sample_climate_df.to_csv(csv_file, index=False)
        ingestor = ClimateFactorsIngestor(csv_path=csv_file)
        bronze_df = ingestor.ingest(output_dir=tmp_path)
        silver_df = encode_climate_silver(bronze_df)

        summary = compute_climate_summary(silver_df)
        assert "mean_temperature_c" in summary
        assert "mean_precipitation_mm" in summary
        assert "mean_climate_stress_index" in summary
        assert summary["n_scenarios"] == 4


class TestPRDWeatherCompliance:
    def test_weather_disabled_by_default(self, sample_gold_panel):
        config = {
            "features": {
                "lags": [1, 2, 3],
                "rolling_windows": [7],
                "horizon_days": [1, 3],
                "use_weather": False,  # PRD 4.6 default
            }
        }
        feat_df = build_features(sample_gold_panel, config=config, use_calendar=False)
        assert feat_df["weather_temp_mean"].isna().all()
        assert feat_df["weather_rain_7d"].isna().all()

    def test_weather_enabled_with_real_observations(self, sample_gold_panel):
        config = {
            "features": {
                "lags": [1, 2, 3],
                "rolling_windows": [7],
                "horizon_days": [1, 3],
                "use_weather": True,
            }
        }
        weather_df = pd.DataFrame({
            "mandi_id": ["mandi_1"] * 60,
            "date": sample_gold_panel["date"],
            "weather_temp_mean": [28.0] * 60,
            "weather_rain_7d": [12.5] * 60,
        })
        feat_df = build_features(sample_gold_panel, config=config, use_calendar=False, weather_df=weather_df)
        assert not feat_df["weather_temp_mean"].isna().all()
        assert np.isclose(feat_df["weather_temp_mean"].iloc[0], 28.0)


class TestPRDShockRadar:
    def test_robust_z_shock_detection(self):
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        prices = pd.Series(2000.0, index=dates)
        # Normal flat prices -> no shock at z=3.0
        shocks = detect_shocks(prices, z_threshold=3.0, lookback_window=30)
        assert shocks["is_shock"].sum() == 0

        # Inject extreme price shock at day 45 (+50%)
        prices.iloc[45] = 3000.0
        shocks_spiked = detect_shocks(prices, z_threshold=3.0, lookback_window=30)
        assert shocks_spiked["is_shock"].iloc[45] is np.True_ or bool(shocks_spiked["is_shock"].iloc[45]) is True

    def test_evaluate_radar_state_watch_and_shock(self, sample_gold_panel, tmp_path):
        # Event file with verified policy shock
        events_file = tmp_path / "events.csv"
        pd.DataFrame([{
            "date": "2024-02-01",
            "event_type": "export_ban",
            "crop": "soybean",
            "description": "Export ban imposed",
            "source": "DGFT",
            "impact_direction": "down",
            "verified": True,
        }]).to_csv(events_file, index=False)

        state = evaluate_radar_state(
            current_date="2024-02-03",
            crop="soybean",
            gold_panel=sample_gold_panel,
            events_csv_path=events_file,
            z_threshold=3.0,
        )
        assert state["level"] == RadarLevel.SHOCK
        assert "S4 Policy Event Shock" in state["reason"]
