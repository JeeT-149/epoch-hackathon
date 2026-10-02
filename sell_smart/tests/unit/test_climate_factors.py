"""
sell_smart.tests.unit.test_climate_factors
Unit tests for climate factors ingestion, silver encoding, summary statistics,
feature building, and confidence adjustments.
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
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    df = pd.DataFrame({
        "mandi_id": ["mandi_1"] * 30,
        "crop": ["soybean"] * 30,
        "date": dates,
        "modal_price": [2000.0 + i * 5 for i in range(30)],
        "min_price": [1900.0 + i * 5 for i in range(30)],
        "max_price": [2100.0 + i * 5 for i in range(30)],
        "arrivals_qt": [100.0] * 30,
        "is_imputed": [False] * 30,
        "days_since_observed": [0] * 30,
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
        assert "disease_incidence_enc" in silver_df.columns
        assert "water_availability_enc" in silver_df.columns

        # Verify stress index is in [0, 1]
        assert (silver_df["climate_stress_index"] >= 0.0).all()
        assert (silver_df["climate_stress_index"] <= 1.0).all()

        # Drought and Heatwave are extreme events
        assert bool(silver_df.loc[silver_df["extreme_weather_type"] == "Drought", "is_extreme_event"].iloc[0]) is True
        assert bool(silver_df.loc[silver_df["extreme_weather_type"] == "Storm", "is_extreme_event"].iloc[0]) is False


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
        assert "shock_prior_probability" in summary
        assert summary["n_scenarios"] == 4
        assert 0.0 <= summary["shock_prior_probability"] <= 1.0


class TestFeatureIntegration:
    def test_climate_activates_weather_features(self, sample_gold_panel):
        config = {
            "features": {
                "lags": [1, 2, 3],
                "rolling_windows": [7],
                "horizon_days": [1, 3],
                "use_weather": False,
            }
        }
        climate_summary = {
            "mean_temperature_c": 30.5,
            "mean_precipitation_mm": 45.2,
            "mean_climate_stress_index": 0.42,
            "p95_climate_stress_index": 0.75,
            "high_disease_rate": 0.25,
            "low_water_rate": 0.30,
            "shock_prior_probability": 0.60,
        }
        feat_df = build_features(
            sample_gold_panel,
            config=config,
            use_calendar=False,
            climate_summary=climate_summary,
        )

        assert not feat_df["weather_temp_mean"].isna().all()
        assert np.isclose(feat_df["weather_temp_mean"].iloc[0], 30.5)
        assert np.isclose(feat_df["weather_rain_7d"].iloc[0], 45.2)
        assert np.isclose(feat_df["climate_stress_index"].iloc[0], 0.42)
        assert np.isclose(feat_df["disease_incidence_enc"].iloc[0], 0.25)
        assert np.isclose(feat_df["water_stress_enc"].iloc[0], 0.30)


class TestConfidenceAdjustment:
    def test_climate_adjusts_confidence(self):
        config = {
            "confidence": {
                "dq_weight": 0.4,
                "model_weight": 0.3,
                "economics_weight": 0.3,
                "thresholds": {"HIGH": 0.70, "MEDIUM": 0.45},
            }
        }
        # Without climate summary
        _, score_base = compute_confidence(
            dq_score=0.9,
            model_interval_width=50.0,
            modal_price=2000.0,
            is_placeholder=False,
            config=config,
        )

        # With high climate stress / disease
        climate_summary = {
            "high_disease_rate": 0.8,
            "low_water_rate": 0.8,
        }
        _, score_climate = compute_confidence(
            dq_score=0.9,
            model_interval_width=50.0,
            modal_price=2000.0,
            is_placeholder=False,
            config=config,
            climate_summary=climate_summary,
        )

        # Confidence should be strictly lower under high climate stress
        assert score_climate < score_base
