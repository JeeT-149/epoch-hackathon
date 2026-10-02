# Sell Smart ML & Decision Pipeline Execution Summary

- **Execution Timestamp**: 2026-10-02T21:10:05.978476+00:00
- **Total Execution Time**: 56.22 seconds
- **Status**: SUCCESS

## Summary of Executed Stages:
1. **Stage 1 (Bronze Ingestion)**: Ingested 60,565 total raw observations (`data/raw/prices_bronze.parquet`) and 1,000 climate risk scenarios (`data/raw/climate_factors_bronze.parquet`).
2. **Stage 2 (Silver Canonicalization)**: Cleaned, deduplicated, flagged outliers (rolling MAD $k=6$) across Soybean, Onion, and Tomato (`data/silver/prices_daily.parquet`); encoded climate silver scenarios (`data/silver/climate_factors_silver.parquet`).
3. **Stage 3 (Mandi Selection)**: Selected 24 APMC mandis using coverage and gap constraints (`config/mandis.yaml`).
4. **Stage 4 (Gold Feature Engineering)**: Generated past-only features with strict zero-leakage assertions and activated climate risk features (`data/gold/features_panel.parquet`).
5. **Stage 5 (Quantile Modeling & Conformal)**: Trained 90 LightGBM Quantile models across 5 horizons and 5 quantiles; computed Calibration Passports (`artifacts/calibration_passport.json`).
6. **Stage 6 (Decision Intelligence)**: Evaluated net-return options factoring in transport, storage, climate risk confidence discount, and non-linear spoilage curves for 50 farmer scenarios.
   - Recommendation breakdown: `{'sell_now': 50}`
   - Results: `reports/farmer_decision_batch_results.csv`
7. **Stage 7 (Triggers & Receipts)**: Verified Climate-informed Shock Radar (z=2.0), state machine transitions, and generated farmer Regret Receipts.
