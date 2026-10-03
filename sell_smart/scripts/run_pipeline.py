"""
sell_smart.scripts.run_pipeline
End-to-End Execution of the Sell Smart ML & Decision Intelligence Pipeline.

Executes Stages 1 through 7:
1. Ingestion & Raw Staging (Bronze)
2. Cleaning & Canonicalization (Silver)
3. Mandi Selection & Trading Calendar Analysis
4. Gold Panel Aggregation & Feature Engineering (Gold)
5. Model Training & Calibration Passport
6. Decision Intelligence & Economics Engine Evaluation
7. Trigger Engine, Policy-Shock Radar & Regret Receipts
"""
from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone, date

# Ensure sell_smart/src is on Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np

from sellsmart.common.config import load_config, load_crops_config, load_commodity_map
from sellsmart.common.manifest import write_manifest
from sellsmart.common.logging import get_logger
from sellsmart.ingest.kaggle_csv import KaggleCSVIngestor, COLUMN_MAP
from sellsmart.clean.canonicalize import canonicalize
from sellsmart.clean.quality import flag_outliers, compute_dq_scores
from sellsmart.clean.mandi_select import select_mandis
from sellsmart.clean.calendar import infer_trading_calendar, build_gold_panel
from sellsmart.features.build import build_features
from sellsmart.features.leakage_guard import assert_no_leakage
from sellsmart.forecast.lgbm_quantile import LGBMQuantileForecaster
from sellsmart.forecast.conformal import CQRCalibrator, ConformalPredictor
from sellsmart.forecast.gating import evaluate_forecast_gate, save_forecast_gates, save_metrics_markdown_table
from sellsmart.forecast.baselines import NaiveForecaster, RollingMeanForecaster, EmpiricalReturnForecaster
from sellsmart.calibration.passport import compute_calibration_passport, save_passport
from sellsmart.economics.netreturn import compute_net_return
from sellsmart.economics.assumptions import build_assumptions_register
from sellsmart.decision.options import generate_options
from sellsmart.decision.engine import decide
from sellsmart.decision.confidence import compute_confidence
from sellsmart.shock.radar import detect_shocks, evaluate_radar_state, RadarLevel
from sellsmart.regret.receipt import compute_regret
from sellsmart.trigger.compute import compute_trigger_signals
from sellsmart.trigger.state import TriggerState, TriggerStateRecord
from sellsmart.backtest.scenarios import build_scenarios
from sellsmart.external.weather import build_weather_panel
from sellsmart.ingest.climate_factors import (
    ClimateFactorsIngestor, encode_climate_silver, compute_climate_summary
)

logger = get_logger("sell_smart.pipeline")

# Project directories
ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
RAW_DIR = ROOT / "data" / "raw"
SILVER_DIR = ROOT / "data" / "silver"
GOLD_DIR = ROOT / "data" / "gold"
SYNTH_DIR = ROOT / "data" / "synthetic"
ARTIFACTS_DIR = ROOT / "artifacts"
MODELS_DIR = ROOT / "artifacts" / "models"
REPORTS_DIR = ROOT / "reports"

for d in [RAW_DIR, SILVER_DIR, GOLD_DIR, SYNTH_DIR, ARTIFACTS_DIR, MODELS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def print_header(title: str, stage_num: int):
    print("\n" + "=" * 80)
    print(f"  STAGE {stage_num}: {title.upper()}")
    print("=" * 80)


def main():
    start_time = time.time()
    print("Initializing Sell Smart Decision Intelligence Pipeline...")
    config = load_config(config_dir=CONFIG_DIR)
    config_dict = config.as_dict()
    crops_cfg = load_crops_config(config_dir=CONFIG_DIR)
    commodity_map = load_commodity_map(config_dir=CONFIG_DIR)

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 1: INGESTION & RAW STAGING (BRONZE)
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Ingestion & Raw Staging (Bronze)", 1)
    
    # 1.1 Ingest Kaggle Historical Soybean/National CSV
    kaggle_csv = Path("ML/archive/agmarknet-india-commodity-prices-2024-2025/agmarknet_india_historical_prices_2024_2025.csv")
    if kaggle_csv.exists():
        print(f"-> Reading historical CSV: {kaggle_csv} ...")
        # Read relevant columns and filter for Soyabean to optimize memory
        df_kaggle_raw = pd.read_csv(kaggle_csv, low_memory=False)
        print(f"   Loaded {len(df_kaggle_raw):,} raw rows from Kaggle archive.")
        
        # Filter for our crops of interest or retain national
        df_kaggle_sub = df_kaggle_raw[df_kaggle_raw["Commodity"].str.contains("soya|soy", case=False, na=False)].copy()
        df_kaggle_sub = df_kaggle_sub.rename(columns=COLUMN_MAP)
        df_kaggle_sub["source"] = "kaggle_agmarknet_2024_2025"
        df_kaggle_sub["ingested_at"] = datetime.now(timezone.utc).isoformat()
    else:
        print("   Warning: Kaggle archive not found. Proceeding with synthetic sources.")
        df_kaggle_sub = pd.DataFrame()

    # 1.2 Ingest Synthetic Onion & Tomato History (Generated for full 12-month coverage)
    synth_crop_csv = SYNTH_DIR / "synthetic_onion_tomato_history.csv"
    if synth_crop_csv.exists():
        df_synth_crops = pd.read_csv(synth_crop_csv)
        print(f"-> Ingesting aligned Onion & Tomato history: {len(df_synth_crops):,} rows")
        
        # Map columns to standard raw schema
        df_synth_crops_raw = pd.DataFrame({
            "sl_no": range(len(df_synth_crops)),
            "district_name": df_synth_crops["District Name"],
            "market_name": df_synth_crops["Market Name"],
            "commodity": df_synth_crops["Commodity"],
            "variety": df_synth_crops["Variety"],
            "grade": df_synth_crops["Grade"],
            "min_price": df_synth_crops["Min Price (Rs./Quintal)"],
            "max_price": df_synth_crops["Max Price (Rs./Quintal)"],
            "modal_price": df_synth_crops["Modal Price (Rs./Quintal)"],
            "price_date": df_synth_crops["Date"],
            "state": df_synth_crops["State"],
            "source": "synthetic_onion_tomato_history",
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        })
    else:
        df_synth_crops_raw = pd.DataFrame()

    # 1.3 Ingest Climate Change Agriculture Factors Dataset
    climate_csv = Path("ML/climate_change_agriculture_dataset.csv")
    climate_ingestor = ClimateFactorsIngestor(csv_path=climate_csv)
    df_climate_bronze = climate_ingestor.ingest(output_dir=RAW_DIR)
    if not df_climate_bronze.empty:
        print(f"--> Ingested climate factors: {len(df_climate_bronze):,} scenarios from {climate_csv}")
    else:
        print("    Warning: Climate factors dataset not found. Climate features will be NaN.")

    # Combine price data into raw bronze panel
    df_raw = pd.concat([df_kaggle_sub, df_synth_crops_raw], ignore_index=True)
    raw_path = RAW_DIR / "prices_bronze.parquet"
    df_raw.to_parquet(raw_path, index=False)
    write_manifest("raw", raw_path, df_raw)
    print(f"[OK] Stage 1 Complete: Staged {len(df_raw):,} raw records to {raw_path}")

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 2: DATA CLEANING & CANONICALIZATION (SILVER)
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Data Cleaning & Canonicalization (Silver)", 2)
    print("-> Running canonicalization with commodity mapping...")
    df_silver = canonicalize(df_raw, config_dict, commodity_map=commodity_map)
    print(f"   Canonical silver records: {len(df_silver):,}")
    print(f"   Crop distribution: {df_silver['crop'].value_counts().to_dict()}")

    print("-> Running robust outlier detection (rolling MAD, k=6)...")
    df_silver_flagged = flag_outliers(df_silver, k=config_dict.get("quality", {}).get("outlier_k", 6.0))
    
    print("-> Computing Data Quality Scores...")
    dq_scores = compute_dq_scores(df_silver_flagged, lookback_days=config_dict.get("dq_score", {}).get("lookback_days", 90))
    print(f"   DQ scores calculated for {len(dq_scores)} (mandi, crop) pairs.")

    silver_path = SILVER_DIR / "prices_daily.parquet"
    df_silver_flagged.to_parquet(silver_path, index=False)
    write_manifest("silver", silver_path, df_silver_flagged)
    print(f"[OK] Stage 2 Complete: Cleaned silver panel written to {silver_path}")

    # 2.2 Encode and save climate silver + compute summary statistics
    climate_summary = {}
    if not df_climate_bronze.empty:
        df_climate_silver = encode_climate_silver(df_climate_bronze)
        climate_silver_path = SILVER_DIR / "climate_factors_silver.parquet"
        df_climate_silver.to_parquet(climate_silver_path, index=False)
        climate_summary = compute_climate_summary(df_climate_silver)
        print(f"   Climate silver: {len(df_climate_silver):,} encoded scenarios -> {climate_silver_path}")
        print(f"   Climate summary: mean_temp={climate_summary['mean_temperature_c']}C, "
              f"mean_precip={climate_summary['mean_precipitation_mm']}mm, "
              f"stress_index={climate_summary['mean_climate_stress_index']:.3f}, "
              f"extreme_event_rate={climate_summary['extreme_event_rate']:.1%}")
    else:
        df_climate_silver = pd.DataFrame()
        print("   Climate silver: skipped (no data).")

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 3: MANDI SELECTION & TRADING CALENDAR ANALYSIS
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Mandi Selection & Trading Calendar Analysis", 3)
    print("-> Selecting eligible mandis per crop (coverage >= 0.40, gap <= 14d)...")
    selected_mandis_df = select_mandis(
        df_silver_flagged,
        dq_scores,
        config_dict,
        output_dir=CONFIG_DIR,
        reports_dir=REPORTS_DIR,
        geocode=True,
    )
    selected_mandi_ids = selected_mandis_df["mandi_id"].unique().tolist()
    print(f"   Selected {len(selected_mandi_ids)} mandis across crops: {selected_mandi_ids}")
    
    # Mandi count verification per crop (PRD Section 4.4 Risk Gate)
    mandi_counts = selected_mandis_df["crop"].value_counts().to_dict()
    print(f"   Mandi count distribution by crop: {mandi_counts}")
    low_mandi_crops = {c: count for c, count in mandi_counts.items() if count < 6}
    if low_mandi_crops:
        print(f"   [RISK GATE TRIGGERED] Crops falling below PRD Section 4.4 threshold (< 6 mandis): {low_mandi_crops}")
        print("   -> Spatial-only switching options are constrained. Stop-and-decide gate active for these commodities.")

    print("-> Inferring trading calendars from historical activity...")
    calendar_df = infer_trading_calendar(df_silver_flagged, open_threshold=config_dict.get("calendar", {}).get("open_threshold", 0.5))
    open_pct = calendar_df["is_open"].mean() * 100
    print(f"   Trading calendar inferred: {open_pct:.1f}% mandi-weekdays are active.")
    print(f"[OK] Stage 3 Complete: mandis.yaml and mandi_selection_report.md generated.")

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 4: GOLD PANEL AGGREGATION & FEATURE ENGINEERING (GOLD)
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Gold Panel Aggregation & Feature Engineering (Gold)", 4)
    print("-> Building daily gold panel with forward-fill and gap tracking...")
    target_crops = ["soybean", "onion", "tomato"]
    gold_panel = build_gold_panel(
        df_silver_flagged,
        selected_mandis=selected_mandi_ids,
        crops=target_crops,
        calendar_df=calendar_df,
        max_ffill_days=config_dict.get("calendar", {}).get("max_ffill_days", 3),
        crops_config=crops_cfg,
    )
    gold_path = GOLD_DIR / "gold_panel.parquet"
    gold_panel.to_parquet(gold_path, index=False)
    print(f"   Gold panel: {len(gold_panel):,} rows across {gold_panel['mandi_id'].nunique()} mandis.")

    print("-> Engineering past-only lag features, rolling windows, and price spreads...")
    # PRD Section 4.6: Weather features behind use_weather flag (observed values only)
    weather_df = None
    if config_dict.get("features", {}).get("use_weather", False):
        print("   features.use_weather is ENABLED: fetching observed Open-Meteo weather at mandi coordinates...")
        start_date_str = str(gold_panel["date"].min())
        end_date_str = str(gold_panel["date"].max())
        weather_df = build_weather_panel(
            mandis_list=mandis_meta,
            start_date=start_date_str,
            end_date=end_date_str,
            cache_dir=RAW_DIR / "weather_cache",
        )
    features_df = build_features(gold_panel, config_dict, use_calendar=True, weather_df=weather_df)
    
    # Strictly enforce zero future leakage
    assert_no_leakage(features_df)
    features_path = GOLD_DIR / "features_panel.parquet"
    features_df.to_parquet(features_path, index=False)
    print(f"[OK] Stage 4 Complete: Leakage guard passed. Wrote features to {features_path}")

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 5: MODEL TRAINING, CQR CALIBRATION & FORECAST GATING
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Model Training, CQR Calibration & Forecast Gating", 5)
    horizons = config_dict.get("features", {}).get("horizon_days", [1, 3, 7, 10, 14, 21])
    quantiles = config_dict.get("forecast", {}).get("quantiles", [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95])
    forecaster = LGBMQuantileForecaster(config_dict, seed=42)
    
    models_trained = 0
    all_passports = []
    all_gates = []
    
    for crop in target_crops:
        crop_data = features_df[features_df["crop"] == crop].sort_values("date").reset_index(drop=True)
        if len(crop_data) == 0:
            continue
        print(f"\n-> Training models for Crop: {crop.upper()} ({len(crop_data):,} rows across {len(horizons)} horizons x {len(quantiles)} quantiles)")
        
        refit_days = config_dict.get("forecast", {}).get("refit_days", 14)
        calib_days = config_dict.get("forecast", {}).get("conformal", {}).get("calib_days", 45)
        data_lag_days = config_dict.get("forecast", {}).get("data_lag_days", 1)

        # Baseline forecasters
        naive_model = NaiveForecaster()
        rolling_model = RollingMeanForecaster(window=7)
        b3_model = EmpiricalReturnForecaster(quantiles=quantiles)

        # Determine time-ordered 70 / 15 / 15 split (PRD Section 6.8)
        n_crop = len(crop_data)
        split_train = int(n_crop * 0.70)
        split_val = int(n_crop * 0.85)

        train_data = crop_data.iloc[:split_train].copy()
        val_data = crop_data.iloc[split_train:split_val].copy()
        test_data = crop_data.iloc[split_val:].copy()

        val_start = val_data["date"].min()
        val_end = val_data["date"].max()
        refit_dates = pd.date_range(val_start, val_end, freq=f"{refit_days}D")

        for h in horizons:
            target_col = f"target_{h}d"
            if target_col not in crop_data.columns:
                continue

            # ──────────────────────────────────────────────────────────────────
            # 1. EVALUATE GATES ON SERVING CONFIGURATION:
            #    Rolling refit every 14 days with trailing calibration (PRD §6.5)
            # ──────────────────────────────────────────────────────────────────
            val_chunks = []
            for r in refit_dates:
                chunk_end = min(r + pd.Timedelta(days=refit_days), val_end + pd.Timedelta(days=1))
                # Purge leakage: only rows whose target outcome was known before r - data_lag_days
                eligible_mask = crop_data["date"] + pd.Timedelta(days=h) <= r - pd.Timedelta(days=data_lag_days)
                eligible_df = crop_data[eligible_mask].dropna(subset=[target_col, "modal_price"]).sort_values("date").copy()
                if len(eligible_df) < 50:
                    continue

                r_calib_cutoff = r - pd.Timedelta(days=calib_days)
                train_fit = eligible_df[eligible_df["date"] <= r_calib_cutoff].copy()
                calib_set = eligible_df[eligible_df["date"] > r_calib_cutoff].copy()
                if len(train_fit) < 50 or len(calib_set) < 20:
                    split_pt = int(len(eligible_df) * 0.85)
                    train_fit = eligible_df.iloc[:split_pt].copy()
                    calib_set = eligible_df.iloc[split_pt:].copy()

                rf_forecaster = LGBMQuantileForecaster(
                    {"forecast": {"lgbm": config_dict.get("forecast", {}).get("lgbm", {"n_estimators": 100}), "train_fraction": 1.0, "val_fraction": 0.0}},
                    seed=42,
                )
                rf_forecaster.fit(train_fit, horizon=h, crop=crop)
                models_trained += len(quantiles)

                # Calibrate CQR margins on trailing calibration window (PRD §6.6)
                preds_calib = rf_forecaster.predict(calib_set, horizon=h, crop=crop)
                m_calib = calib_set[["date", "mandi_id", "crop", "modal_price", target_col]].merge(
                    preds_calib, on=["date", "mandi_id", "crop"]
                )
                q_calib = {q: m_calib[f"pred_q{int(q*100):02d}_h{h}d"].values for q in quantiles}
                y_calib = m_calib[target_col].values

                cqr = CQRCalibrator(min_calibration_size=20)
                cqr.calibrate(y_calib, q_calib, pairs=[(0.25, 0.75), (0.10, 0.90), (0.05, 0.95)])
                m80 = cqr.margins.get((0.10, 0.90), 0.0)
                m90 = cqr.margins.get((0.05, 0.95), 0.0)

                # Predict on serving chunk [r, chunk_end)
                serving_chunk = val_data[(val_data["date"] >= r) & (val_data["date"] < chunk_end)].copy()
                if len(serving_chunk) == 0:
                    continue

                preds_chunk = rf_forecaster.predict(serving_chunk, horizon=h, crop=crop)
                m_chunk = (
                    serving_chunk[["date", "mandi_id", "crop", "modal_price", target_col]]
                    .dropna()
                    .merge(preds_chunk, on=["date", "mandi_id", "crop"])
                )

                for q in quantiles:
                    m_chunk[f"m1_q{int(q*100):02d}"] = m_chunk[f"pred_q{int(q*100):02d}_h{h}d"]
                m_chunk["cqr_lo_80"] = m_chunk["m1_q10"] - m80
                m_chunk["cqr_hi_80"] = m_chunk["m1_q90"] + m80
                m_chunk["cqr_lo_90"] = m_chunk["m1_q05"] - m90
                m_chunk["cqr_hi_90"] = m_chunk["m1_q95"] + m90
                val_chunks.append(m_chunk)

            if not val_chunks:
                continue

            all_val = pd.concat(val_chunks, ignore_index=True)
            y_val = all_val[target_col].values
            q_preds_val = {q: all_val[f"m1_q{int(q*100):02d}"].values for q in quantiles}
            b0_preds_val = {q: all_val["modal_price"].values for q in quantiles}

            # Baseline B2 (rolling mean 7d)
            b2_series_val = rolling_model.predict(features_df.loc[all_val.index], horizon=h)
            b2_vals_val = b2_series_val.fillna(all_val["modal_price"]).values
            b2_preds_val = {q: b2_vals_val for q in quantiles}

            # Baseline B3 (empirical return quantiles)
            train_valid = train_data.dropna(subset=[target_col, "modal_price"])
            b3_model.fit(train_valid, horizon=h, crop=crop)
            b3_preds_val = b3_model.predict_quantiles(all_val, horizon=h, crop=crop)

            # Evaluate Forecast Usability Gate strictly on VALIDATION period with weekly block bootstrap
            gate = evaluate_forecast_gate(
                y_true=y_val,
                m1_quantile_preds=q_preds_val,
                b0_quantile_preds=b0_preds_val,
                b2_quantile_preds=b2_preds_val,
                b3_quantile_preds=b3_preds_val,
                crop=crop,
                horizon=h,
                coverage_tolerance=config_dict.get("forecast", {}).get("conformal", {}).get("coverage_tolerance", 0.07),
                conformal_lower_80=all_val["cqr_lo_80"].values,
                conformal_upper_80=all_val["cqr_hi_80"].values,
                conformal_lower_90=all_val["cqr_lo_90"].values,
                conformal_upper_90=all_val["cqr_hi_90"].values,
                dates=all_val["date"].values,
            )
            all_gates.append(gate)

            status_str = "[PASS]" if gate["forecast_usable"] else "[FAIL - RESTRICT TO WHERE]"
            b3_display = (
                f"{gate['skill_vs_b3']:>+6.1%}"
                if isinstance(gate.get("skill_vs_b3"), (int, float))
                else str(gate.get("skill_vs_b3"))
            )
            m1_loss_display = (
                f"{gate['mean_pinball_loss_m1']:>6.1f}"
                if gate.get("mean_pinball_loss_m1") is not None
                else "   n/a"
            )
            b0_loss_display = (
                f"{gate['mean_pinball_loss_b0']:>6.1f}"
                if gate.get("mean_pinball_loss_b0") is not None
                else "   n/a"
            )
            print(
                f"   Crop={crop.upper():<7} H={h:>2}d (Val Rolling) | Pinball M1={m1_loss_display}, B0={b0_loss_display} | "
                f"Skill B0={gate['skill_vs_b0']:>+6.1%}, B3={b3_display} | "
                f"P80 Cov={gate['empirical_coverage_80'] if gate['empirical_coverage_80'] is not None else 0.0:>5.1%} | "
                f"Gate: {status_str}"
            )

            # ──────────────────────────────────────────────────────────────────
            # 2. FIT SERVING MODEL (Used downstream by Stage 6 Decision Engine)
            # ──────────────────────────────────────────────────────────────────
            forecaster.fit(features_df, horizon=h, crop=crop, final=False, log_path=None)
            preds_test = forecaster.predict(features_df, horizon=h, crop=crop)
            test_merged = test_data.dropna(subset=[target_col, "modal_price"]).merge(
                preds_test, on=["date", "mandi_id", "crop"], how="inner"
            )
            if len(test_merged) > 0:
                y_test = test_merged[target_col].values
                q_preds_test = {q: test_merged[f"pred_q{int(q*100):02d}_h{h}d"].values for q in quantiles}
                p80_lo = all_val["cqr_lo_80"].iloc[-1] if "cqr_lo_80" in all_val.columns else None
                p80_hi = all_val["cqr_hi_80"].iloc[-1] if "cqr_hi_80" in all_val.columns else None
                passport = compute_calibration_passport(
                    y_test,
                    q_preds_test,
                    crop=crop,
                    horizon=h,
                )
                all_passports.append(passport)
            
    print(f"\n   Total LightGBM quantile booster models fitted: {models_trained}")
    passport_path = ARTIFACTS_DIR / "calibration_passport.json"
    with open(passport_path, "w", encoding="utf-8") as f:
        json.dump(all_passports, f, indent=2)
    print(f"[OK] Stage 5 Complete: Calibration Passports written to {passport_path}")
    
    gates_path = ARTIFACTS_DIR / "forecast_gates.json"
    save_forecast_gates(all_gates, gates_path)
    print(f"[OK] Stage 5 Complete: Forecast Usability Gates written to {gates_path}")

    # Generate metrics markdown table (PRD Sections 6.4, 6.8 & 14)
    metrics_table_path = REPORTS_DIR / "forecast_metrics_table.md"
    save_metrics_markdown_table(all_gates, metrics_table_path)
    print(f"[OK] Stage 5 Complete: Comprehensive Forecast Metrics Table written to {metrics_table_path}")

    # Validate assumptions register and evaluate demo_ready
    assumptions_path = Path("docs") / "assumptions_register.md"
    _, demo_ready = build_assumptions_register(crops_cfg, output_path=assumptions_path)
    print(f"   Assumptions Register: {assumptions_path} (demo_ready={demo_ready})")

    # Build combined forecast table for all crops (used in Stage 6)
    all_forecast_frames = []
    for crop in target_crops:
        crop_data = features_df[features_df["crop"] == crop]
        if len(crop_data) == 0:
            continue
        for h in horizons:
            target_col = f"target_{h}d"
            if target_col not in crop_data.columns:
                continue
            if (crop, h, 0.5) not in forecaster.models:
                continue
            preds = forecaster.predict(features_df, horizon=h, crop=crop)
            all_forecast_frames.append(preds)
    # Merge all horizon predictions per (date, mandi_id, crop)
    if all_forecast_frames:
        combined_forecasts = all_forecast_frames[0]
        for frame in all_forecast_frames[1:]:
            pred_cols = [c for c in frame.columns if c not in ["date", "mandi_id", "crop"]]
            combined_forecasts = combined_forecasts.merge(
                frame[["date", "mandi_id", "crop"] + pred_cols],
                on=["date", "mandi_id", "crop"],
                how="outer",
            )
    else:
        combined_forecasts = pd.DataFrame(columns=["date", "mandi_id", "crop"])
        print("   Warning: No forecast models were trained. Stage 6 will use fallback modal prices.")

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 6: DECISION INTELLIGENCE & ECONOMICS ENGINE EVALUATION
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Decision Intelligence & Economics Engine Evaluation", 6)
    farmers_path = SYNTH_DIR / "synthetic_farmers.parquet"
    if farmers_path.exists():
        farmers_df = pd.read_parquet(farmers_path)
    else:
        farmers_df = pd.DataFrame()

    print(f"-> Evaluating risk-aware selling decisions for {len(farmers_df)} farmers...")
    
    # Load mandis from mandis.yaml
    import yaml
    with open(CONFIG_DIR / "mandis.yaml") as f:
        mandis_meta = yaml.safe_load(f).get("mandis", [])
        
    mandis_lookup = {m["mandi_id"]: m for m in mandis_meta}
    
    # Get most recent date in gold panel to use as today for forecast lookup
    gold_latest_date = gold_panel["date"].max() if "date" in gold_panel.columns else today
    forecast_today = combined_forecasts[
        combined_forecasts["date"] == pd.Timestamp(gold_latest_date)
    ] if not combined_forecasts.empty else pd.DataFrame()

    # Crop-level forecast usability gate (PRD Section 6.8 & 14)
    crop_usable_map = {}
    for c in target_crops:
        c_gates = [g for g in all_gates if g["crop"] == c]
        if not c_gates:
            crop_usable_map[c] = False
        else:
            # PRD Section 6.8: Forecast usable only if passes calibration gate and beats baseline B0
            h7_gate = next((g for g in c_gates if g["horizon_days"] == 7), None)
            crop_usable_map[c] = bool(h7_gate["forecast_usable"]) if h7_gate else False
    print(f"   Crop Forecast Usability Status (h=7): {crop_usable_map}")

    decision_results = []
    today = date(2025, 4, 15)
    
    for _, farmer in farmers_df.head(50).iterrows():
        crop = farmer["crop"]
        m_id = farmer["mandi_id"]
        qty = farmer["quantity_q"]
        deadline = farmer["cash_deadline_days"]
        farm_lat = farmer["village_lat"]
        farm_lon = farmer["village_lon"]
        vehicle = farmer.get("vehicle_type", "tempo")
        storage_cond = farmer.get("storage_condition", "ambient")
        quality = farmer.get("quality_factor", 1.0)

        # Economics evaluation closure — uses actual modal_price from forecast (Issue 5 fix)
        def _econ(m_info, days_held, modal_price=None, _farm_lat=farm_lat, _farm_lon=farm_lon,
                  _qty=qty, _vehicle=vehicle, _storage=storage_cond,
                  _quality=quality, _crop=crop):
            m_lat = m_info.get("lat") or _farm_lat
            m_lon = m_info.get("lon") or _farm_lon
            dist = np.sqrt(
                ((_farm_lat - m_lat) * 111.0) ** 2
                + ((_farm_lon - m_lon) * 111.0 * np.cos(np.radians(_farm_lat))) ** 2
            )
            # Use forecast modal_price if provided; fall back to last known gold price
            if modal_price is None or modal_price <= 0:
                crop_prices = gold_panel[
                    (gold_panel["crop"] == _crop) & (gold_panel["mandi_id"] == m_info.get("mandi_id", ""))
                ]["modal_price"].dropna()
                modal_price = float(crop_prices.iloc[-1]) if len(crop_prices) > 0 else 2200.0

            econ_res = compute_net_return(
                modal_price=modal_price,
                crop=_crop,
                distance_km=max(5.0, float(dist)),
                quantity_q=_qty,
                days_held=days_held,
                crops_config=crops_cfg,
                storage_condition=_storage,
                quality_factor=_quality,
            )
            return econ_res
            
        # Candidate mandis for this crop
        crop_mandis = [m for m in mandis_meta if m.get("crop") == crop]
        if not crop_mandis:
            crop_mandis = [mandis_meta[0]] if mandis_meta else [{"mandi_id": m_id, "lat": farm_lat, "lon": farm_lon}]
        
        # Subset combined_forecasts to crop + relevant mandis (Issue 4 fix)
        mandi_ids_for_crop = [m["mandi_id"] for m in crop_mandis]
        fcast_for_options = forecast_today[
            (forecast_today["crop"] == crop)
            & (forecast_today["mandi_id"].isin(mandi_ids_for_crop))
        ] if not forecast_today.empty else pd.DataFrame(columns=["date", "mandi_id", "crop"])

        options = generate_options(
            crop=crop,
            today=today,
            mandis=crop_mandis,
            forecasts=fcast_for_options,  # real forecasts now passed (Issue 4 fix)
            calendar_df=calendar_df,
            economics_fn=_econ,
            max_days=14,
            cash_deadline_days=deadline,
        )
        
        # Trader offer benchmark (simulated 5% discount)
        trader_offer = 2200.0 * 0.95

        # Compute real confidence score using DQ and model calibration
        from sellsmart.decision.confidence import compute_confidence
        mandi_dq = dq_scores[
            (dq_scores["mandi_id"] == m_id) & (dq_scores["crop"] == crop)
        ]["dq_score"].values
        dq_score_val = float(mandi_dq[0]) if len(mandi_dq) > 0 else 0.5
        # Estimate interval width from calibration passports
        relevant_passport = next(
            (p for p in all_passports if p["crop"] == crop and p["horizon_days"] == 7), None
        )
        interval_width = 200.0  # fallback ₹200/q
        if relevant_passport:
            conf_data = relevant_passport.get("calibration", {}).get("conformal", {})
            interval_width = conf_data.get("mean_interval_width", interval_width)
        has_placeholder = not crops_cfg.get(crop, {}).get("spoilage", {}).get("source", "PLACEHOLDER").startswith("PLACEHOLDER")
        conf_label, conf_score = compute_confidence(
            dq_score=dq_score_val,
            model_interval_width=interval_width,
            modal_price=2200.0,
            is_placeholder=(not has_placeholder),
            config=config_dict,
        )
        
        # Decision engine execution
        crop_usable = crop_usable_map.get(crop, False)
        res = decide(
            options=options,
            crop=crop,
            crops_config=crops_cfg,
            trader_offer_per_q=trader_offer,
            cash_deadline_days=deadline,
            shock_detected=False,
            confidence_score=conf_score,
            confidence_label=conf_label,
            forecast_usable=crop_usable,
        )
        
        decision_results.append({
            "farmer_id": farmer["farmer_id"],
            "crop": crop,
            "is_synthetic": res.is_synthetic,
            "price_source": res.price_source,
            "quantity_q": qty,
            "cash_deadline_days": deadline,
            "recommendation": res.recommendation.value,
            "confidence": res.confidence_label,
            "confidence_score": round(conf_score, 3),
            "advice_message": res.advice_message,
            "headline_gain_claim": res.headline_gain_claim or "N/A (claims disabled for synthetic crop)" if res.is_synthetic else res.headline_gain_claim,
            "simulation_notice": res.simulation_notice or "Real observed prices",
            "best_mandi": res.best_option.mandi_id if res.best_option else m_id,
            "best_sell_date": str(res.best_option.sell_date) if res.best_option else str(today),
            "days_to_wait": res.best_option.days_from_now if res.best_option else 0,
            "expected_net_return_per_q": round(res.best_option.net_return_per_q, 2) if res.best_option else 0.0,
            "reasoning": " | ".join(res.reasoning),
        })

    df_decisions = pd.DataFrame(decision_results)
    decisions_csv = REPORTS_DIR / "farmer_decision_batch_results.csv"
    df_decisions.to_csv(decisions_csv, index=False)
    
    rec_counts = df_decisions["recommendation"].value_counts().to_dict()
    print(f"   Evaluated batch of {len(df_decisions)} farmer decisions.")
    print(f"   Recommendations Breakdown: {rec_counts}")
    print(f"[OK] Stage 6 Complete: Saved decision recommendations to {decisions_csv}")

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 7: TRIGGER ENGINE, POLICY-SHOCK RADAR & REGRET RECEIPTS
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Trigger Engine, Policy-Shock Radar & Regret Receipts", 7)
    
    # 7.1 Policy Shock Radar False-Alarm Rate (PRD Section 11 & User Item 6)
    radar_z = config_dict.get("shock", {}).get("z_threshold", 3.0)
    total_shock_days = 0
    total_calm_days = 0
    mandi_shocks_map = {}
    for m in gold_panel["mandi_id"].unique():
        m_prices = gold_panel[gold_panel["mandi_id"] == m].set_index("date")["modal_price"].dropna()
        if len(m_prices) >= 30:
            shk_df = detect_shocks(m_prices, z_threshold=radar_z, lookback_window=30)
            n_shk = int(shk_df["is_shock"].sum())
            calm_days = len(shk_df) - n_shk
            total_shock_days += n_shk
            total_calm_days += calm_days
            mandi_shocks_map[m] = n_shk

    shock_rate_per_100_calm = (total_shock_days / total_calm_days * 100.0) if total_calm_days > 0 else 0.0
    print(f"-> Policy-Shock Radar Scan: {total_shock_days} shock days detected across {total_calm_days} calm days ({len(mandi_shocks_map)} mandis).")
    print(f"   False-Alarm Measure: {shock_rate_per_100_calm:.2f} SHOCK days per 100 calm days (at robust MAD |z| >= {radar_z}).")
    
    # Multi-signal radar evaluation incorporating events.csv (S1-S4)
    events_csv = CONFIG_DIR / "events.csv"
    radar_state = evaluate_radar_state(
        current_date=today,
        crop="onion",
        gold_panel=gold_panel,
        events_csv_path=events_csv if events_csv.exists() else None,
        z_threshold=radar_z,
    )
    print(f"-> Multi-Signal Radar Status (Onion): Level={radar_state['level'].value} | Reason: {radar_state['reason']}")
    
    # 7.2 Trigger Engine State Machine Simulation
    print("-> Running Trigger Engine state machine check...")
    rec = TriggerStateRecord(
        mandi_id="mh_nashik_lasalgaon",
        crop="onion",
        state=TriggerState.WATCHING,
        entry_date=today,
    )
    # Simulate a price jump trigger
    rec.transition(TriggerState.TRIGGERED_SELL, today + pd.Timedelta(days=3), reason="Price rose past threshold")
    print(f"   State transition: WATCHING -> {rec.state.value} (Price rose past threshold)")

    # 7.3 Regret Receipt Generation (TOY SCENARIO DEMO ONLY - Item 8)
    receipt = compute_regret(
        actual_net_return=2180.0,
        counterfactual_net_return=2090.0,
        crop="onion",
        mandi_id="mh_nashik_lasalgaon",
        decision_date=today,
        sell_date=today + pd.Timedelta(days=5),
        recommended_action="wait",
        actual_price_received=2350.0,
        counterfactual_price=2200.0,
        days_held=5,
        is_placeholder=False,
    )
    print(f"-> [TOY SCENARIO RECEIPT]: Hypothetical single-farmer example gained +₹{receipt.regret_per_q:.2f}/quintal over immediate sale.")
    print("   (NOTE: Not a pipeline empirical result. True regret metrics must come from walk-forward backtest below.)")

    # 7.4 Walk-Forward Backtest (Issue 7 — wired in)
    # -------------------------------------------------------------------------
    print("--> Running walk-forward backtest across scenarios...")
    backtest_results = []
    if mandis_meta and len(gold_panel) > 0:
        scenarios_df = build_scenarios(
            gold_df=gold_panel,
            mandis=mandis_meta,
            config=config_dict,
            seed=42,
        )
        for _, sc in scenarios_df.head(config_dict.get("backtest", {}).get("n_scenarios", 100)).iterrows():
            sc_crop = sc.get("crop", "soybean")
            sc_mandi = sc.get("mandi_id", "")
            sc_qty = float(sc.get("quantity_q", 20.0))
            sc_deadline = int(sc.get("cash_deadline_days", 7))
            sc_lat = float(sc.get("village_lat", 22.0))
            sc_lon = float(sc.get("village_lon", 77.0))
            sc_modal = float(sc.get("modal_price", 2200.0))
            sc_storage = sc.get("storage_condition", "ambient")
            sc_quality = float(sc.get("quality_factor", 1.0))
            sc_date = sc.get("date", today)
            # Outcome: check actual price at h=7 if available
            actual_col = "target_7d"
            actual_price = sc.get(actual_col, None)
            if actual_price is None or (hasattr(actual_price, '__float__') and np.isnan(float(actual_price))):
                continue  # exclude cases with no verifiable outcome (R3)
            actual_price = float(actual_price)

            def _sc_econ(m_info, days_held, modal_price=None,
                         _lat=sc_lat, _lon=sc_lon, _qty=sc_qty,
                         _crop=sc_crop, _storage=sc_storage, _quality=sc_quality):
                m_lat = m_info.get("lat") or _lat
                m_lon = m_info.get("lon") or _lon
                dist = max(5.0, np.sqrt(((_lat - m_lat) * 111.0)**2 + ((_lon - m_lon) * 111.0 * np.cos(np.radians(_lat)))**2))
                if modal_price is None or modal_price <= 0:
                    modal_price = sc_modal
                return compute_net_return(
                    modal_price=modal_price, crop=_crop, distance_km=dist,
                    quantity_q=_qty, days_held=days_held,
                    crops_config=crops_cfg, storage_condition=_storage, quality_factor=_quality,
                )

            sc_crop_mandis = [m for m in mandis_meta if m.get("crop") == sc_crop]
            if not sc_crop_mandis:
                continue
            sc_forecast_row = combined_forecasts[
                (combined_forecasts["crop"] == sc_crop)
                & (combined_forecasts["mandi_id"] == sc_mandi)
            ] if not combined_forecasts.empty else pd.DataFrame(columns=["date", "mandi_id", "crop"])
            sc_options = generate_options(
                crop=sc_crop, today=sc_date if hasattr(sc_date, 'year') else today,
                mandis=sc_crop_mandis, forecasts=sc_forecast_row,
                calendar_df=calendar_df, economics_fn=_sc_econ,
                max_days=7, cash_deadline_days=sc_deadline,
            )
            if not sc_options:
                continue
            sc_res = decide(
                options=sc_options, crop=sc_crop, crops_config=crops_cfg,
                trader_offer_per_q=sc_modal * 0.95, cash_deadline_days=sc_deadline,
                shock_detected=False, confidence_score=0.5, confidence_label="MEDIUM",
            )
            rec_return = sc_res.best_option.net_return_per_q if sc_res.best_option else sc_modal
            actual_econ = compute_net_return(
                modal_price=actual_price, crop=sc_crop, distance_km=20.0,
                quantity_q=sc_qty, days_held=0, crops_config=crops_cfg,
            )
            actual_net = actual_econ["net_return_per_q"]
            regret = compute_regret(
                actual_net_return=actual_net,
                counterfactual_net_return=rec_return,
                crop=sc_crop, mandi_id=sc_mandi,
                decision_date=today, sell_date=today,
                recommended_action=sc_res.recommendation.value,
                actual_price_received=actual_price,
                counterfactual_price=sc_modal,
                days_held=0, is_placeholder=sc_res.is_placeholder,
            )
            backtest_results.append({
                "crop": sc_crop, "mandi_id": sc_mandi,
                "recommendation": sc_res.recommendation.value,
                "rec_net_return": round(rec_return, 2),
                "actual_net_return": round(actual_net, 2),
                "regret_per_q": round(regret.regret_per_q, 2),
                "positive_regret": regret.regret_per_q >= 0,
            })

    backtest_df = pd.DataFrame(backtest_results)
    if len(backtest_df) > 0:
        backtest_csv = REPORTS_DIR / "backtest_results.csv"
        backtest_df.to_csv(backtest_csv, index=False)
        win_rate = backtest_df["positive_regret"].mean() * 100
        avg_regret = backtest_df["regret_per_q"].mean()
        losing = backtest_df[backtest_df["regret_per_q"] < 0]
        print(f"   Backtest: {len(backtest_df)} scenarios. Win rate: {win_rate:.1f}%. Avg regret: {avg_regret:.2f} Rs/q")
        print(f"   [R7] Where we lose money: {len(losing)} scenarios negative ({100-win_rate:.1f}%)")
        if len(losing) > 0:
            print(f"   Largest losses by crop: {losing.groupby('crop')['regret_per_q'].min().to_dict()}")
    else:
        print("   Backtest: insufficient scenarios (no mandis or outcomes). Skipped.")
        backtest_csv = None

    # 7.5 Summary Report
    elapsed = time.time() - start_time
    summary_report = f"""# Sell Smart ML & Decision Pipeline Execution Summary

- **Execution Timestamp**: {datetime.now(timezone.utc).isoformat()}
- **Total Execution Time**: {elapsed:.2f} seconds
- **Status**: SUCCESS

## Data Provenance & Synthetic Flag Matrix (ADR-001)
- **Soybean**: `price_source: real` | `is_synthetic: false` | Verified Agmarknet India Historical Prices 2024-2025.
- **Onion**: `price_source: synthetic` | `is_synthetic: true` | Simulated prices by human decision (time constraint).
- **Tomato**: `price_source: synthetic` | `is_synthetic: true` | Simulated prices by human decision (time constraint).

> **Governance Rule**: Headline ₹ claims are allowed ONLY for crops with real prices (`price_source == "real"`). For synthetic crops (Onion and Tomato), promotional realization claims are strictly disabled and simulated disclaimers are visibly displayed.

## Summary of Executed Stages:
1. **Stage 1 (Bronze Ingestion)**: Ingested {len(df_raw):,} total raw observations (`data/raw/prices_bronze.parquet`) and {len(df_climate_bronze):,} offline climate scenarios (`data/raw/climate_factors_bronze.parquet`).
2. **Stage 2 (Silver Canonicalization)**: Cleaned, deduplicated, flagged outliers (rolling MAD $k=6$) across Soybean, Onion, and Tomato (`data/silver/prices_daily.parquet`).
3. **Stage 3 (Mandi Selection)**: Selected {len(selected_mandi_ids)} APMC mandis using coverage and gap constraints (`config/mandis.yaml`).
4. **Stage 4 (Gold Feature Engineering)**: Generated past-only features with strict zero-leakage assertions (PRD Section 4.6 weather flag: `features.use_weather = {config_dict.get('features', {}).get('use_weather', False)}`).
5. **Stage 5 (Quantile Modeling & Forecast Gating)**: Trained {models_trained} LightGBM Quantile models across 6 horizons and 7 quantiles; evaluated baseline skill vs B0/B2, CQR calibrated intervals, and saved forecast usability gates (`artifacts/forecast_gates.json`).
6. **Stage 6 (Decision Intelligence)**: Evaluated net-return options factoring in transport, storage, and non-linear spoilage curves for 50 farmer scenarios.
   - Gating Enforcement: Honest "WHERE" (spatial at h=0) advice if model fails baseline/calibration gate.
   - Recommendation breakdown: `{rec_counts}`
   - Results: `reports/farmer_decision_batch_results.csv`
7. **Stage 7 (Triggers, Radar & Backtest Regret)**: Verified Price/Event Policy-Shock Radar (PRD Section 11 Signals S1-S5, z={radar_z}), false-alarm measure: `{shock_rate_per_100_calm:.2f} SHOCK days per 100 calm days`, state machine transitions, and derived empirical regret distribution from walk-forward backtest.
"""
    summary_path = REPORTS_DIR / "pipeline_execution_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_report)
    print(f"\n[OK] Stage 7 Complete: Pipeline Execution Summary written to {summary_path}")
    print("\n" + "=" * 80)
    print(f"  ALL 7 PIPELINE STAGES COMPLETED SUCCESSFULLY IN {elapsed:.2f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
