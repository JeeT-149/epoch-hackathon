# Sell Smart ML & Decision Pipeline Execution Summary

- **Execution Timestamp**: 2026-10-02T23:30:44.784160+00:00
- **Total Execution Time**: 508.72 seconds
- **Status**: SUCCESS

## Data Provenance & Synthetic Flag Matrix (ADR-001)
- **Soybean**: `price_source: real` | `is_synthetic: false` | Verified Agmarknet India Historical Prices 2024-2025.
- **Onion**: `price_source: synthetic` | `is_synthetic: true` | Simulated prices by human decision (time constraint).
- **Tomato**: `price_source: synthetic` | `is_synthetic: true` | Simulated prices by human decision (time constraint).

> **Governance Rule**: Headline ₹ claims are allowed ONLY for crops with real prices (`price_source == "real"`). For synthetic crops (Onion and Tomato), promotional realization claims are strictly disabled and simulated disclaimers are visibly displayed.

## Summary of Executed Stages:
1. **Stage 1 (Bronze Ingestion)**: Ingested 60,565 total raw observations (`data/raw/prices_bronze.parquet`) and 1,000 offline climate scenarios (`data/raw/climate_factors_bronze.parquet`).
2. **Stage 2 (Silver Canonicalization)**: Cleaned, deduplicated, flagged outliers (rolling MAD $k=6$) across Soybean, Onion, and Tomato (`data/silver/prices_daily.parquet`).
3. **Stage 3 (Mandi Selection)**: Selected 24 APMC mandis using coverage and gap constraints (`config/mandis.yaml`).
4. **Stage 4 (Gold Feature Engineering)**: Generated past-only features with strict zero-leakage assertions (PRD Section 4.6 weather flag: `features.use_weather = False`).
5. **Stage 5 (Quantile Modeling & Forecast Gating)**: Trained 504 LightGBM Quantile models across 6 horizons and 7 quantiles; evaluated baseline skill vs B0/B2, CQR calibrated intervals, and saved forecast usability gates (`artifacts/forecast_gates.json`).
6. **Stage 6 (Decision Intelligence)**: Evaluated net-return options factoring in transport, storage, and non-linear spoilage curves for 50 farmer scenarios.
   - Gating Enforcement: Honest "WHERE" (spatial at h=0) advice if model fails baseline/calibration gate.
   - Recommendation breakdown: `{'SELL_NOW_NEAREST': 50}`
   - Results: `reports/farmer_decision_batch_results.csv`
7. **Stage 7 (Triggers, Radar & Backtest Regret)**: Verified Price/Event Policy-Shock Radar (PRD Section 11 Signals S1-S5, z=3.0), false-alarm measure: `7.58 SHOCK days per 100 calm days`, state machine transitions, and derived empirical regret distribution from walk-forward backtest.
