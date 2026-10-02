# Sell Smart: ML & Decision Intelligence PRD

**Version:** 1.0  |  **Date:** 2 Oct 2026  |  **Audience:** an AI coding agent (e.g. Antigravity) building the ML/decision backend end to end
**Product concept:** Fair-Price Guardian (farmer experience) powered by a Trigger Engine (decision intelligence)

> Sell Smart is a risk-aware agricultural decision engine that checks a farmer's current trader offer against future mandi opportunities and tells them whether to **sell now, wait, or switch markets**, accounting for transport, spoilage, storage, cash deadlines and uncertainty.

It is **not** a price-prediction app, a mandi-price viewer, or a chatbot. The forecast is an input. The product is the **decision**.

---

## 0. How you (the agent) must work

1. Read this whole document before writing code.
2. Build strictly in the order of **Section 18 (Phases)**. Do not start optional modules before core acceptance criteria (Section 19) pass.
3. Every phase ends with: passing tests, a generated artifact in `reports/` or `artifacts/`, and an entry in `docs/DECISIONS.md`.
4. If something is ambiguous, choose the simplest option consistent with this document, record the choice and reason in `docs/DECISIONS.md`, and keep going. Ask the human only if blocked.
5. **Never fabricate** numbers, citations, policy events, coordinates, API behaviour, or performance results. If an external fact is needed (API field names, rate limits, endpoint availability), verify it by reading docs or calling the API. If you cannot verify, mark it `UNVERIFIED` in code comments and in `docs/DECISIONS.md`.
6. Every number a farmer will see must come from deterministic backend code (Section 15). An LLM may only parse input and phrase output.
7. If results are weak, report them honestly and improve the model. Never tune toward a better-looking number on the test period.

---

## 1. Scope

### 1.1 In scope (this PRD)
- Data ingestion, cleaning, validation, mandi selection (Agmarknet-style daily prices)
- Optional exogenous data (weather, distances) and synthetic scenario generators
- Baseline and quantile price forecasting with calibrated uncertainty
- Crop-specific spoilage, storage, transport and fee economics (config-driven)
- Decision Engine (mandi x selling day), cash-deadline constraint, risk-aware recommendation
- Trigger Engine (threshold, deadline, daily monitoring, state machine, events)
- Confidence labelling, Policy-Shock Radar, Crisis Replay data products, Regret Receipt
- Walk-forward backtest with baselines, ablations and loss analysis
- Calibration Passport
- A FastAPI service exposing all of the above as JSON
- Reproducibility, tests and auto-generated reports

### 1.2 Out of scope (interfaces only)
- WhatsApp integration, speech-to-text, text-to-speech, dashboard UI
- LLM parsing/phrasing implementation (this PRD defines only the **contract**, Section 15)
- Optional modules: FPO Splitter, Anti-Herd Dispatch, Photo-to-Shelf-Life (Section 17 has stubs; do not build until core is accepted)

### 1.3 Crops
Tomato, Onion, Soybean. **Do not use one generic model or one generic spoilage curve.** Crop behaviour differs:

| Crop | Core question | Hold plausibility |
|---|---|---|
| Tomato | WHERE to sell | Short window; hold rarely worthwhile |
| Onion | WHERE and HOW LONG | Hold plausible; storage/rot/humidity and policy shocks matter |
| Soybean | WHEN, given quality and cash need | Low physical spoilage; moisture/grade and policy (MSP) matter |

The engine must encode this through crop config (e.g. `max_storage_days`, spoilage curve, `hold_allowed_default`), not through hard-coded `if crop == ...` logic scattered in code.

---

## 2. Hard rules (non-negotiable)

| # | Rule |
|---|---|
| R1 | **LLM boundary.** No price, forecast, spoilage rate, transport cost, recommendation number or trigger threshold may originate from an LLM. |
| R2 | **No leakage.** Features for a decision at date `t` use only information with timestamp <= `t`. No future prices, arrivals, weather or events. Enforced by tests (Section 16). |
| R3 | **Time-ordered splits only.** No random train/test splits. Targets that extend past a split boundary are purged. |
| R4 | **Test period is touched once.** Thresholds, hyperparameters and policies are tuned on validation only. Final test runs require `--final` and are logged to `reports/test_access_log.json`. |
| R5 | **Synthetic data is always labelled.** See Section 4.7. Synthetic columns never enter model features. Every report discloses synthetic inputs. |
| R6 | **No placeholders in demo-ready output.** Economics/spoilage parameters with `source: PLACEHOLDER` make `demo_ready=false` and print a warning banner in every report and API response. |
| R7 | **Losses are reported.** The backtest report must contain a "Where we lose money" section. |
| R8 | **Units.** All money is **₹ per original quintal harvested** (before spoilage). Prices are ₹/quintal. Dates are ISO-8601 in storage. |
| R9 | **Modal price is a proxy.** Agmarknet modal price is a market-level reference, not what a given farmer receives. Every decision output carries this flag. |
| R10 | **Reproducibility.** Seeded randomness, config hash and data hash in every run manifest. |
| R11 | **No unsupported claims.** Never claim guaranteed profit, exact realisation price, perfect spoilage or policy prediction. Language is "decision support under uncertainty". |
| R12 | **Core before flashy.** If a task does not improve the decision, its reliability, or the proof it works, deprioritise it. |

---

## 3. Tech stack & repository layout

**Stack:** Python 3.11, pandas, pyarrow, numpy, scipy, scikit-learn, LightGBM, pydantic v2, FastAPI, uvicorn, PyYAML, httpx, joblib, matplotlib, pytest. Optional: optuna (validation-only tuning), duckdb, streamlit (report viewer).

```text
sell_smart/
  config/
    default.yaml                # Appendix A
    crops.yaml                  # per-crop economics + spoilage (with source registry)
    commodity_map.yaml          # human-confirmed commodity/variety mapping
    mandis.yaml                 # selected mandis + coordinates (generated, human-reviewed)
    events.csv                  # policy/market events (EMPTY template, human-filled)
    messages.yaml               # slot-based message templates
  data/
    raw/                        # bronze: untouched source files
    silver/                     # cleaned canonical tables (parquet)
    gold/                       # model panels / features (parquet)
    synthetic/                  # ALL synthetic data lives here only
  src/sellsmart/
    ingest/        (kaggle_csv.py, datagov_api.py, base.py)
    clean/         (canonicalize.py, quality.py, mandi_select.py, calendar.py)
    external/      (weather.py, geo.py, distance.py)
    synth/         (farmers.py, offers.py, stress.py)
    features/      (build.py, leakage_guard.py)
    forecast/      (baselines.py, lgbm_quantile.py, conformal.py, interpolate.py, registry.py)
    economics/     (spoilage.py, transport.py, storage.py, fees.py, netreturn.py)
    decision/      (options.py, engine.py, confidence.py, reliability.py)
    trigger/       (compute.py, monitor.py, state.py, events.py)
    shock/         (radar.py, replay.py)
    regret/        (receipt.py)
    backtest/      (scenarios.py, simulate.py, metrics.py, ablations.py, report.py)
    calibration/   (passport.py, plots.py)
    api/           (main.py, schemas.py, deps.py)
    common/        (config.py, logging.py, manifest.py, disclaimers.py)
  scripts/         (run_phase*.py, daily_refresh.py, build_reports.py)
  tests/           (unit/, integration/, golden/, leakage/)
  reports/  artifacts/  docs/ (DECISIONS.md, assumptions_register.md)
```

---

## 4. Data layer

### 4.1 Sources (pluggable ingestion)

Implement an `Ingestor` interface so the primary source can change without touching downstream code.

| Source | Role | Notes |
|---|---|---|
| **Kaggle "Agmarknet India Commodity Prices (Oct'24 - Aug'25)"** | Development / prototype source | See 4.2 for its known limits. |
| **data.gov.in Agmarknet variety-wise daily prices API** | Live feed for the Trigger Engine | The second sample dataset used field names like `Min_x0020_Price`, which indicates API origin. Verify current endpoint, key requirement, pagination and rate limits before relying on it. Needs an API key from env var `DATAGOV_API_KEY`. |
| **Longer multi-year history** (e.g. CEDA Ashoka cleaned Agmarknet, India Data Portal APMC arrivals/prices) | Needed for credible seasonality and backtest | Not yet verified for coverage or terms. Implement the interface and a loader stub; the human will supply files. |
| **Open-Meteo historical weather API** | Optional weather features | Verify available daily variables (rainfall, temperature, humidity). If humidity is not offered daily, aggregate from hourly. |
| **OSRM / other routing** | Road distance | Fallback: haversine x `road_factor` (config, flagged as an assumption). |

### 4.2 Primary dev dataset: known schema and limits

Columns: `Sl no.`, `District Name`, `Market Name`, `Commodity`, `Variety`, `Grade`, `Min Price (Rs./Quintal)`, `Max Price (Rs./Quintal)`, `Modal Price (Rs./Quintal)`, `Price Date` (format like `05 Apr 2025`).

Window: **2024-08-15 to 2025-08-14 (12 months)**, roughly 1.1M rows.

Known limits the code must handle explicitly, not hide:
1. **No State column.** Maharashtra must be identified from district names (36 districts, with aliases such as Ahmednagar/Ahilyanagar, Aurangabad/Chhatrapati Sambhajinagar, Osmanabad/Dharashiv). Some district names occur in several states (e.g. Aurangabad also exists in Bihar). Produce `reports/maharashtra_filter_review.csv` listing ambiguous district/market combinations, and verify candidates by geocoding the market (distance to Maharashtra bounding region) before accepting. Human reviews the list.
2. **No arrivals.** Keep a dormant `arrivals_qt` path (column, lags, rolling features) that activates automatically when a source provides arrivals. Meanwhile use only **activity proxies** (4.6) and label them as proxies, never as arrivals.
3. **Only 12 months.** Consequences the code must enforce:
   - Seasonal-naive baseline needs a year-ago value; it is **not evaluable** for most dates. Compute it where possible, otherwise report `n/a (insufficient history)`. Never silently skip.
   - Calendar-seasonality features (month, day-of-year) are **disabled** unless history >= `features.calendar_min_years` (default 2).
   - Season-wise backtest results are single observations per season. The report must say they are anecdotal.
   - The 2023-24 onion export-restriction period is outside this window. Crisis Replay must work from whatever shocks the data contains plus a clearly labelled synthetic stress test.
4. **Stale.** Ends Aug 2025. It cannot drive live monitoring. The live path uses the API ingestor.
5. **Naming inconsistencies exist** (e.g. "Green Chilli" vs "Green Chilly" appeared in column summaries). Expect variants for the three crops.
6. `Sl no.` restarts and is not a unique key. Do not use it as an ID.

### 4.3 Pipeline

```text
raw (bronze) -> silver (cleaned canonical rows) -> gold (daily mandi x crop panel + features) -> models -> decisions
```

Write every stage to parquet with a manifest (row counts, min/max date, hash).

### 4.4 Cleaning & canonicalisation rules (silver)

Canonical silver table `prices_daily`:

| column | type | note |
|---|---|---|
| date | date | parsed with explicit format; fail loudly on unparseable rate > 0.1% |
| state | str, nullable | derived for Maharashtra via 4.2(1); null if unknown |
| district | str | trimmed, title-cased, alias-mapped |
| mandi_id | str | stable slug, e.g. `mh_nashik_lasalgaon` |
| market_raw | str | original |
| crop | enum | `onion`, `tomato`, `soybean` (others dropped from model panels) |
| commodity_raw, variety_raw | str | originals |
| grade | str | e.g. FAQ / Non-FAQ |
| min_price, max_price, modal_price | float | ₹/quintal |
| dq_flags | list[str] | e.g. `inconsistent_minmax`, `suspect_outlier`, `duplicate_conflict` |
| source, ingested_at | | provenance |

Rules:
1. Strip whitespace, normalise case/punctuation, map aliases. Commodity matching uses regexes in `commodity_map.yaml` (e.g. soybean must match both `Soyabean` and `Soybean`).
2. **Human-confirmation step:** for Maharashtra, print the unique commodity strings and variety strings matching each crop with row counts, write a proposed `commodity_map.yaml`, and stop for review. If no human reply is available, proceed with the highest-coverage variety per crop and record it in `DECISIONS.md`.
3. Drop exact duplicate rows. For conflicting duplicates on `(date, mandi, commodity, variety, grade)`, take the median and set `duplicate_conflict`.
4. Drop rows with `modal_price <= 0` or null. If `min <= modal <= max` is violated, set `inconsistent_minmax` and exclude from features (retain in silver).
5. Outliers: per `(mandi, crop)` rolling median +/- `k` x MAD (`quality.outlier_k`, default 6). Flag as `suspect_outlier`. Suspect rows are excluded from features and are **never** used as the "current price" in a decision. Do not hard-code price ranges; use robust statistics.
6. Gold panel aggregation: one row per `(mandi_id, crop, date)`. Prefer grade FAQ and the crop's canonical variety; if several rows remain, take the median of modal and record `n_source_rows`.

### 4.5 Trading calendar, gaps, mandi selection

- **Trading calendar (inferred from data, not assumed):** for each mandi and weekday, the mandi is "open" if it reported on >= `calendar.open_threshold` (default 0.5) of that weekday's dates. Selling-day options are only generated on open days. Unknown or low-data mandis default to Mon-Sat flagged `calendar_assumed`.
- **Gap handling:** forward-fill modal price up to `max_ffill_days` (default 3) with a `days_since_obs` feature. Beyond that, leave NaN (LightGBM handles it).
- **Target availability:** target at `t+h` is the observed modal on that exact date, or the nearest observed within `target_tolerance_days` (default 0; allowed 1, flagged). Rows without a target are dropped from training. In the backtest, cases whose outcome cannot be realised are **excluded and counted**, never imputed.
- **Data Quality Score** per `(mandi, crop)` in [0,1]: weighted mix of coverage over the last 90 days, inverse longest-gap penalty, recency of last observation, and (1 - suspect rate). Weights in config. Used in confidence labelling.
- **Mandi selection per crop** (target 10-15 mandis, selected on data quality, not popularity): require coverage >= `mandi_select.min_coverage`, longest gap <= `mandi_select.max_gap_days`, and recency. Among eligible, prefer geographic spread within `mandi_select.max_radius_km` of the demo region (Nashik) so that "switch mandi" is meaningful. Candidates to check first: Lasalgaon, Pimpalgaon, Nashik, Pune, Latur, Akola, plus others the data supports. Output `reports/mandi_selection_report.md` with coverage, gaps and the reason each mandi was kept or rejected. If fewer than 10 qualify for a crop, report that honestly and proceed with what exists.
- **Mandi coordinates:** geocode each selected mandi via a geocoding service, store in `mandis.yaml` with a `geocode_confidence` field, and flag low-confidence entries for human review. **Never invent coordinates.**

### 4.6 Optional exogenous data

| Data | Use | Rules |
|---|---|---|
| Weather (rain, temperature, humidity) at mandi coordinates | Features: trailing 7/14-day rainfall sum, mean/max temperature | Observed values up to `t` only. Never forecasted weather. Behind `features.use_weather` flag; ablate its value. If the API is unreachable, disable weather features. **Do not synthesise weather.** |
| Diesel price | Optional transport-rate adjustment / feature | Low priority; likely near-constant over 12 months |
| Festival calendar | Calendar flags | Human supplies the table; skip if absent |
| MSP table (soybean) | Reference feature/flag | Human supplies; skip if absent |
| Neighbouring-state mandi prices | Cross-mandi features | Allowed since the dataset is national; pick nearby states' mandis by coordinates |

### 4.7 Synthetic data policy

Synthetic data is allowed **only** for (a) farmer/offer scenarios the real data cannot supply, (b) unit-test fixtures, (c) stress tests, (d) clearly labelled demo content.

Rules:
1. All synthetic output lives in `data/synthetic/` with columns `is_synthetic=True`, `generator`, `seed`, `config_hash`.
2. **No synthetic column may be a model feature or a forecast target.** A unit test asserts that the feature list and synthetic column list are disjoint.
3. **Do not synthesise prices, weather, spoilage outcomes, or arrivals for the forecasting/backtest pipeline.** If arrivals are unavailable, they are absent, not faked.
4. Every report prints a "Synthetic inputs used" box listing the generators and their parameters.

Permitted synthetic columns:

| Column | Generator | Used for | Notes |
|---|---|---|---|
| `farmer_id`, `village_lat`, `village_lon` | Sample points around mandi clusters: distance U(`synth.village_km_min`, `synth.village_km_max`) from the nearest selected mandi, random bearing | Backtest scenarios | Taluka-level locations are acceptable for a prototype |
| `quantity_q` | Sampled from `synth.quantity_choices` (e.g. 10, 20, 50, 100) | Transport cost per quintal | |
| `vehicle_type` | Smallest vehicle in `crops.yaml` with capacity >= quantity; multiple trips if needed | Transport | |
| `cash_deadline_days` | Sampled from {0, 3, 7, 14, 21} with configurable weights | Feasibility constraint | Maps the farmer's "when do you need the money?" answer |
| `storage_condition` | Sampled per crop from config levels | Spoilage multiplier | |
| `quality_factor` | Config distribution (e.g. soybean moisture/grade proxy) | Spoilage/price haircut | |
| `trader_offer_proxy` | `nearest_mandi_modal(t0) x (1 - delta)`, `delta ~ distribution` in `synth.offer_discount` (default: mixture including `delta=0` as the strict case) | Backtest comparison vs trader offer | **Not real offers.** Headline results use the **no-offer baseline (sell at nearest mandi today)**. Offer-based results are reported per delta regime. |
| `stress_shock_series` | Inject a labelled jump/regime change into a copy of a real series | Radar unit test and a clearly labelled "synthetic stress demo" | Never presented as a real event |
| `demo_arrivals_index` | Optional, demo/FPO mockups only | UI mockups | **Never** used by forecasting or backtest |

Golden unit-test fixtures (also synthetic) must exist: a deterministic rising-price series (engine should WAIT), a falling series (SELL NOW), a flat series (ACCEPT), and a shock series (hold suspended).

