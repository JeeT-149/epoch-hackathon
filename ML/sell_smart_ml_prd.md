# Sell Smart: ML & Decision Intelligence PRD

**Version:** 2.0 (final, consolidated)  |  **Date:** 3 Oct 2026  |  **Audience:** an AI coding agent (e.g. Antigravity) building the ML/decision backend end to end
**Product concept:** Fair-Price Guardian (farmer experience) powered by a Trigger Engine (decision intelligence)

> Sell Smart is a risk-aware agricultural decision engine that checks a farmer's current trader offer against future mandi opportunities and tells them whether to **sell now, wait, or switch markets**, accounting for transport, spoilage, storage, cash deadlines and uncertainty.

It is **not** a price-prediction app, a mandi-price viewer, or a chatbot. The forecast is an input. The product is the **decision**.


## Table of contents

0. How you (the agent) must work
1. Scope
2. Hard rules (non-negotiable)
3. Tech stack & repository layout
4. Data layer (sources, dev dataset limits, cleaning, calendar, mandi selection, synthetic data policy)
5. Product behaviour & decision outputs
6. Forecasting (time definitions, features, baselines, quantile models, conformal calibration, gating)
7. Economics (net return, spoilage, transport, storage, fees, parameter provenance)
8. Decision Engine
9. Trigger Engine
10. Confidence labelling
11. Policy-Shock Radar & Crisis Replay
12. Regret Receipt
13. Walk-forward backtest
14. Calibration Passport
15. Interfaces: FastAPI contract and LLM boundary
16. Testing & leakage guards
17. Optional modules (FPO Splitter and others)
18. Build phases (and minimum viable subset)
19. Acceptance criteria
20. Reports, artifacts and run manifest
21. Risks, assumptions and open items for the human
- Appendix A: `config/default.yaml`
- Appendix B: `config/crops.yaml` skeleton (all values PLACEHOLDER)
- Appendix C: `config/messages.yaml` examples
- Appendix D: Data audit script, `DECISIONS.md` and assumptions-register templates
- Appendix E: Glossary

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

- **Trading calendar (inferred from data, not assumed):** for each mandi and weekday, the mandi is "open" if it reported on >= `calendar.open_threshold` (default 0.5) of that weekday's dates. Selling-day options are only generated on open days. Unknown or low-data mandis default to Mon-Sat flagged `calendar_assumed`. (Config keys in this PRD are written in dotted shorthand; Appendix A is the authoritative key list.)
- **Gap handling:** forward-fill modal price up to `data.max_ffill_days` (default 3) with a `days_since_obs` feature. Beyond that, leave NaN (LightGBM handles it).
- **Target availability:** target at `t+h` is the observed modal on that exact date, or the nearest observed within `data.target_tolerance_days` (default 0; allowed 1, flagged). Rows without a target are dropped from training. In the backtest, cases whose outcome cannot be realised are **excluded and counted**, never imputed.
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

---

## 5. Product behaviour & decision outputs

### 5.1 Farmer journey (interface-agnostic; the ML service must support exactly this)

1. **Inputs from the interface layer:** `crop`, `quantity_q`, `village` (text or coordinates), optional `trader_offer_per_q` (₹/quintal quoted by a trader), optional `storage_available`.
2. **One question:** "When do you need the money?" mapped to `cash_deadline_days` in {0, 3, 7, 14, 21}. If unanswered, use `decision.default_cash_deadline_days` and set `deadline_assumed=true` in the response so the interface can ask again.
3. **Advice:** the engine returns one decision status (5.2) with a structured payload (net amounts, likely range, confidence, reason codes, trigger plan if any).
4. **Standing order:** if the status is `WAIT_WITH_TRIGGER`, the Trigger Engine monitors daily and emits an event **only** when something changes (trigger fired, deadline near, plan revised, shock suspended). The farmer is never asked to check prices.
5. **Outcome:** when the farmer reports the actual sale (optional), a Regret Receipt is produced (Section 12).

### 5.2 Decision statuses

| Status | Meaning | Typical case |
|---|---|---|
| `ACCEPT_OFFER` | The trader's offer is within the safety margin of the best feasible alternative, or alternatives are not reliably better | Offer is fair |
| `SWITCH_MARKET_NOW` | Selling today at another mandi gives a clearly better net than the reference, with required probability | Tomato, or onion with a better mandi 40 km away |
| `WAIT_WITH_TRIGGER` | Holding is feasible and beats the reference with required probability after spoilage, storage and transport. Returns target price, deadline and fallback | Onion with storage; soybean with a loose cash deadline |
| `SELL_NOW_NEAREST` | No offer given and the nearest mandi today is the best feasible option | Nothing beats it |
| `NO_CONFIDENT_ADVICE` | The reference action itself cannot be computed (no usable current price and no offer) | Data outage |

Every response also carries `caution_flags` (for example `shock_caution`, `modal_price_proxy`, `deadline_assumed`, `demo_ready_false`, `calib_small`, `data_stale`).

### 5.3 Crop behaviour is configuration, not code

Tomato mostly returns `SWITCH_MARKET_NOW` or `ACCEPT_OFFER` because holding is rarely worthwhile ("where", not "when"). Onion can return all statuses. Soybean's `WAIT` depends mostly on the cash deadline and the quality factor. This must emerge from `crops.yaml` parameters (`max_storage_days`, spoilage, `hold_allowed_default`) interacting with real forecasts. Do not hard-code outcomes.

### 5.4 Language constraints for all outputs

Use "typical (median) outcome" and "likely range". Never say "guaranteed", "you will earn", or "the price will be". Always state the reference the gain is measured against (trader offer, or nearest-mandi sale today).

---

## 6. Forecasting

### 6.1 Time definitions (the realism contract)

| Term | Definition |
|---|---|
| `as_of` | The date on which a decision is made |
| `data_lag_days` | Reporting delay (default 1; **UNVERIFIED**, a third-party source says Agmarknet is typically 1-2 days behind). The latest usable observation for a decision at `as_of` has date <= `as_of - data_lag_days` |
| `h` | Days from `as_of` to the planned selling day. `h = 0` means sell on `as_of` |
| `execution_lag_days` | When a trigger fires on observed data of day `d`, the earliest sale is the next open day >= `d + execution_lag_days` (default 1). The realised price is that day's price, not the day-`d` price |
| `horizon set` | Trained horizons H = {1, 3, 7, 10, 14, 21}. Other `h` are interpolated (6.7). `h = 0` uses the latest observed price at the chosen mandi (no forecast) |

Because of `data_lag_days`, a decision at `as_of` forecasts from information that is already `data_lag_days` old. Features are built from observations dated <= `as_of - data_lag_days`, and the target is the modal price on `as_of + h`. This must be identical in training, backtest and live use.

### 6.2 Targets

Per (mandi, crop, as_of, h): `y = log(P[mandi, as_of + h] / P_ref)` where `P_ref` is the last usable observed modal price for that mandi (after gap handling). Predicting a relative change makes pooling across mandis possible and removes level drift. Convert back to ₹/quintal for outputs: `P_q = P_ref * exp(y_q)`.

### 6.3 Feature families (all strictly <= `as_of - data_lag_days`)

| Family | Features | Notes |
|---|---|---|
| Own price history | log-ratios of lagged modal prices vs `P_ref` at lags 1, 2, 3, 7, 14, 21, 28; rolling mean/std/min/max over 7, 14, 28 days; momentum (7d and 14d change); `days_since_obs` | Gaps via 4.5 |
| Cross-mandi | Regional median of other selected mandis' latest price for the same crop; own-vs-regional spread; lagged changes of the top-k neighbours chosen by **trailing** correlation computed on training data only (k = `features.neighbour_k`, default 3) | Doubles as the optional "lead-lag" signal; keep it as a feature and as a "why" reason code, not a separate product |
| Activity proxies | Mandi reporting rate over last 7 days, number of source rows (variety/grade lines) that day, number of mandis reporting that day, `(max-min)/modal` spread | **Proxies, not arrivals.** Label them as such everywhere |
| Arrivals (dormant) | `arrivals_qt` lags and rolling sums | Activates only when a source provides arrivals (4.2) |
| Calendar | day-of-week always; month/day-of-year only if history >= `features.calendar_min_years` | Disabled by default with 12 months |
| Events | Flags from `events.csv` with `event_date <= as_of` | Human-filled; empty template by default |
| Weather (optional) | Trailing 7/14-day rainfall sum, mean/max temperature at mandi coordinates | `features.use_weather`; observed only; ablate |
| Static | `mandi_id` (categorical), crop | Crop-specific models, so crop is implicit |

A `leakage_guard` module must reject any feature whose source timestamp exceeds `as_of - data_lag_days`, and tests (Section 16) must prove it.

### 6.4 Models

| ID | Model | Role |
|---|---|---|
| B0 | Persistence: `P_ref` with empirical return quantiles | Mandatory baseline |
| B1 | Seasonal naive (price one year earlier) | Evaluate only where a year-ago value exists, otherwise report `n/a (insufficient history)` |
| B2 | EWMA / rolling-mean level with empirical return quantiles | Mandatory baseline |
| B3 | Empirical return distribution: trailing-window quantiles of h-day log returns per crop and mandi cluster | Strong simple probabilistic baseline |
| M1 | **LightGBM quantile regression**, pooled per (crop, horizon, quantile), `mandi_id` categorical | Primary model |
| M2 (optional) | A pretrained time-series foundation model or Prophet-style model as an ensemble/ablation member | Only after M1 is accepted; must be verified, not assumed to help |

Quantile set Q = {0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95}. Fix quantile crossing by sorting predictions per row, and count how often sorting was needed (report it).

### 6.5 Training protocol: rolling refit with trailing calibration

For each refit date `r` (every `forecast.refit_days`, default 14):

1. Eligible training rows are those whose target date satisfies `as_of + h <= r - data_lag_days` (outcome already known at `r`). This purges leakage across the boundary.
2. Split eligible rows in time: the most recent `conformal.calib_days` (default 45) of rows form the **calibration set**; everything earlier is `train_fit`. Calibration rows are strictly later than `train_fit` rows.
3. Fit M1 on `train_fit` with early stopping on a time-ordered inner tail of `train_fit` (last 15%). Fixed seeds.
4. Compute conformal margins on the calibration set (6.6).
5. Use this model and margins for all `as_of` in `[r, r + refit_days)`.
6. For live serving, refit on the same schedule and persist `artifacts/models/{crop}/{version}/`.

LightGBM defaults are deliberately conservative because data is small: `num_leaves` 15, `min_data_in_leaf` 40, `learning_rate` 0.05, `feature_fraction` 0.8, `lambda_l2` 5. Hyperparameter search (optional, optuna) uses the **validation period only** (R4).

### 6.6 Conformal calibration (CQR on nested intervals)

For each crop and horizon, calibrate three nested pairs on the calibration set: (0.25, 0.75), (0.10, 0.90), (0.05, 0.95).

For a pair `(lo, hi)` with miscoverage `alpha = lo + (1 - hi)`:
- Score `E_i = max(q_lo_i - y_i, y_i - q_hi_i)`.
- Margin `m = quantile(E, ceil((n + 1) * (1 - alpha)) / n)`.
- Calibrated bounds: `q_lo - m`, `q_hi + m`. Margins may be negative (shrinking over-wide intervals). Enforce nesting: margins non-decreasing outward.
- The median (0.50) is not adjusted.
- If `n < conformal.min_calib_n` (default 100), inflate the margin by `conformal.small_sample_inflation` (default 1.25) and set `calib_small` on the forecast.

Report coverage before and after calibration in the Calibration Passport (Section 14). Note that conformal guarantees assume exchangeability, which time series only approximate. Say so in the report, and rely on the walk-forward coverage numbers rather than the theory.

### 6.7 Horizon interpolation

Interpolate log-return quantile curves linearly in `h` between trained horizons. Do not extrapolate beyond `max(H)` (21 days). Options with `h > max(H)` are not generated.

### 6.8 Forecast gating (honest fallback)

For each (crop, horizon, mandi cluster), compute the validation weighted interval score and pinball loss relative to B0 and B3. A forecast is **usable** only if M1 beats the best baseline on validation, where skill = `1 - loss_M1 / loss_best_baseline` and a forecast is usable if `skill >= forecast.min_skill` (default 0.0, meaning at least as good as the best baseline), **and** its P10-P90 coverage is within `calibration.coverage_tolerance` of nominal. Otherwise:
- Mark `forecast_usable=false` in `artifacts/forecast_gates.json`.
- The Decision Engine restricts that crop and horizon to `h = 0` options and reports reason code `NO_RELIABLE_FORECAST`.
- Confidence is capped at Low for any hold-related statement.

This is an intended behaviour, not a failure. If tomato forecasts do not beat persistence, the product honestly answers "where", not "when".

### 6.9 Forecast output schema

```json
{
  "mandi_id": "mh_nashik_lasalgaon", "crop": "onion", "as_of": "2025-06-10",
  "p_ref": 1480.0, "p_ref_date": "2025-06-09", "h": 7,
  "quantiles": {"0.05": 1390.0, "0.10": 1420.0, "0.25": 1465.0, "0.50": 1510.0,
                "0.75": 1565.0, "0.90": 1620.0, "0.95": 1660.0},
  "model_version": "m1-2025-06-01", "calibrated": true, "calib_small": false,
  "forecast_usable": true, "flags": []
}
```
(Illustrative numbers only.)

---

## 7. Economics (config-driven, all parameters carry provenance)

### 7.1 Net return per original quintal

For an option (mandi `m`, hold days `h`, selling day `d = as_of + h`) and a farmer with `qty` quintals:

```
net(m, h, tau) = P_tau(m, as_of + h) * quality_factor * (1 - weight_loss(crop, h, storage, quality))
                 * (1 - quality_price_discount(crop, h, storage))
                 - transport_per_q(village, m, qty)
                 - fees_per_q(m, price)
                 - storage_cost_per_q(crop, h, storage)
                 - opportunity_cost_per_q(price_now, h)
```

All terms are ₹ per **original** quintal (R8). `P_tau` is the calibrated price quantile at level `tau`. Because `net` is strictly increasing in price and costs are deterministic, the quantiles of net return are obtained by pushing price quantiles through this formula. No sampling is needed.

For `h = 0` options, `P` is the latest observed modal price at mandi `m` (not suspect, not stale) and the spoilage terms are zero.

### 7.2 Spoilage and quality

Two components, both from config:
- **Weight loss** `weight_loss(h)`: cumulative fraction of mass lost after `h` days. Form: `1 - exp(-(h / lambda)^beta)` with crop parameters `lambda`, `beta`, scaled by a storage-condition multiplier.
- **Quality price discount** `quality_price_discount(h)`: fractional price discount from quality degradation (same functional form, separate parameters). It matters for tomato, and for soybean moisture/grade.
- **Hard cut-off:** options with `h > max_storage_days(crop, storage)` are infeasible.
- `quality_factor` (default 1.0) is a farmer-level multiplier from the synthetic or reported quality proxy.

Parameter values must come from published sources (for example ICAR institutes, CIPHET, NHRDF, state agricultural universities) via the source registry in 7.6. The agent must not invent values. Until a human verifies them, they stay `PLACEHOLDER` and R6 applies.

### 7.3 Transport (trip-based, never "per quintal per km" as a primary input)

```
trips            = ceil(qty / vehicle.capacity_q)
cost_per_trip    = vehicle.fixed_cost + vehicle.rate_per_km * road_km * round_trip_factor + loading_cost
transport_per_q  = trips * cost_per_trip / qty
```

- Choose the feasible vehicle with the lowest total cost for the given `qty` from `crops.yaml` vehicle list. Small loads use small vehicles at a worse per-quintal rate, which is realistic.
- `road_km` comes from OSRM when available. Fallback is `haversine_km * road_factor` (config, flagged as an assumption). Cache all distances in `data/silver/distances.parquet`; never call a routing service per request.
- Village locations come from geocoding or the gazetteer. If a village cannot be resolved with adequate confidence, the engine returns a clarification request instead of guessing.
- **Plausibility guard (mandatory):** compute implied `₹ per quintal per km` for every vehicle and warn if it falls outside `economics.transport_plausible_range` (placeholder band, human-set). Also warn when `transport_per_q` exceeds `economics.transport_max_share_of_price` of the price for the median option. A flat "₹ per km per quintal" figure that makes a 40 km haul cost a large share of the price is a configuration error until proven otherwise. Do not hide the warning.

### 7.4 Storage and opportunity cost

- `storage_cost_per_q(crop, h, storage)`: ₹ per quintal per day by storage condition (on-farm, ventilated, cold), from config.
- `opportunity_cost_per_q(price_now, h) = price_now * daily_rate * h` with `economics.holding_rate_per_day` (default 0 until a sourced value is set). It represents the cost of cash locked in produce.

### 7.5 Fees

Per mandi or default: commission %, market fee %, hamali/loading ₹/q, weighing ₹/q, each with `paid_by: seller|buyer`. Deduct only seller-paid items. Source and verification status are mandatory. Trader offers are assumed to be at farm gate with no further deductions unless the request supplies `known_deductions_per_q` (config default 0, flagged).

### 7.6 Parameter provenance and the source registry

Every economic or spoilage parameter in `crops.yaml` has:

```yaml
transport:
  vehicles:
    - name: small_pickup
      capacity_q: 15
      rate_per_km: 14.0
      source: PLACEHOLDER          # or {id: SRC_001, verified: true}
sources:
  SRC_001: {citation: "...", url: "...", retrieved: "YYYY-MM-DD", verified_by: "human-name"}
```

- On startup, a validator collects all parameters whose source is `PLACEHOLDER` or unverified, writes `docs/assumptions_register.md`, and sets `demo_ready=false` if any exist (R6).
- The agent may search for candidate sources and propose them in `DECISIONS.md` with URLs. A **human** marks `verified: true`.

### 7.7 Sensitivity analysis

For each backtest run, re-evaluate decisions with transport costs, spoilage rates and fees perturbed by `economics.sensitivity_pct` (default +/-25%) and report the fraction of decisions that change status. High flip rates must be called out as a limitation.

---

## 8. Decision Engine

### 8.1 Inputs

`as_of`, `crop`, `qty_q`, `village` (resolved lat/lon), `cash_deadline_days`, `trader_offer_per_q` (nullable), `storage_available` (bool), `storage_condition`, `quality_factor`, `risk_mode` (fixed to `balanced` unless config says otherwise; the user-facing risk dial is cut), plus current data snapshot and the active model and config versions.

### 8.2 Option generation

Options are pairs (mandi `m`, selling day `d`) with:
- `m` in the selected mandis for the crop within `decision.max_haul_km` of the village (default 120 km; **assumption**).
- `d` on mandi open days (4.5), `d >= as_of`, with `h = d - as_of`.
- **Hard constraints (never scores):**
  - `h <= cash_deadline_days`
  - `h <= max_storage_days(crop, storage_condition)`
  - `h = 0` only, if `storage_available = false` (same-trip selling is allowed; holding is not)
  - `h <= max(H)` and `forecast_usable` for (crop, h), otherwise only `h = 0`
  - `h = 0` options require a usable current observation (not suspect, age <= `decision.max_obs_age_days`, default 3)

### 8.3 Net distributions

For each option compute net quantiles using 7.1 at all levels in Q (calibrated). For `h = 0` options, the net distribution is a point value (observed price), and the likely range collapses. Show it as such.

### 8.4 Reference action

`R` is the reference net per quintal against which gains are measured:
- If a trader offer is present: `R = offer - known_deductions` (at farm gate, no transport).
- Else: `R = ` net of selling at the **nearest open mandi today** (`h = 0`).

When an offer is present, the engine also reports the best `h = 0` mandi net and the best hold option net, so the farmer sees all three: offer, best market today, best wait.

### 8.5 Decision rule (risk-aware, tuned on validation only)

For each alternative option `a` (any option other than the reference action):

- `LB(a)` = net at `tau = decision.risk_quantile` (default 0.10).
- `MED(a)` = net at `tau = 0.50`.
- `gain_lb = LB(a) - R`, `gain_med = MED(a) - R`.
- `p_beat(a) = P(net_a > R + margin)`, derived from the net quantile function by monotone piecewise-linear CDF interpolation across Q. Clip to `[0.02, 0.98]` outside the P05-P95 range.
- `utility(a) = MED(a) - lambda * (MED(a) - LB(a))`, with `lambda` set by `risk_mode` (cautious 1.0, balanced 0.5, aggressive 0.2).

Choose `a* = argmax utility` among alternatives satisfying all of:
1. `p_beat(a) >= decision.p_min`
2. `gain_med >= decision.min_gain_rs`
3. `gain_lb >= decision.lb_margin_rs` (may be negative: allows a small tolerated downside)
4. Confidence label for `a` is not Low
5. No active `SHOCK` flag for crop and region if `h > 0`
6. `forecast_usable` for the option's horizon

If `a*` exists: status is `SWITCH_MARKET_NOW` if `h = 0`, or `WAIT_WITH_TRIGGER` if `h > 0`. Otherwise: `ACCEPT_OFFER` if an offer exists, or `SELL_NOW_NEAREST` if not.

The core idea is the draft's trigger rule: **wait or switch only if the downside-protected case still beats the reference by a safety margin.** The parameters `p_min`, `min_gain_rs`, `lb_margin_rs` and `lambda` are tuned on the validation period by grid search (8.6). They must not be set by hand to look good.

### 8.6 Tuning procedure (validation only)

Grid over `p_min` in {0.55 ... 0.85}, `min_gain_rs` as a percentage of price, `lb_margin_rs`, and `lambda`. Objective: maximise mean realised gain vs the no-offer baseline on validation scenarios, subject to constraints `loss_rate <= tuning.max_loss_rate` (fraction of decisions realising less than the reference) and `p10_gain >= tuning.min_p10_gain`. If no setting satisfies the constraints, choose the most conservative setting and report that the engine rarely advises waiting. Log the full grid in `reports/tuning_grid.csv`. Freeze chosen parameters in `artifacts/decision_params.json` before any test run (R4).

### 8.7 Output payload (excerpt)

```json
{
  "status": "WAIT_WITH_TRIGGER",
  "reference": {"type": "trader_offer", "net_per_q": 1480.0},
  "best_now": {"mandi_id": "...", "net_per_q": 1495.0, "h": 0},
  "chosen": {"mandi_id": "mh_nashik_lasalgaon", "h": 6, "date": "2025-06-16",
             "net_per_q": {"p10": 1530.0, "p50": 1620.0, "p90": 1700.0},
             "gain_vs_reference_per_q": {"p10": 50.0, "p50": 140.0, "p90": 220.0},
             "p_beat": 0.74},
  "confidence": "Medium",
  "reason_codes": ["HOLD_GAIN_EXCEEDS_SPOILAGE", "CASH_DEADLINE_BINDING"],
  "trigger": {"target_price_per_q": 1620.0, "deadline": "2025-06-16", "fallback": "SELL_AT_BEST_AVAILABLE"},
  "caution_flags": ["modal_price_proxy"],
  "demo_ready": false, "synthetic_inputs": ["trader_offer_proxy"]
}
```
(Illustrative numbers only.)

### 8.8 Reason codes (closed set)

`BEST_MARKET_HIGHER_NET`, `HOLD_GAIN_EXCEEDS_SPOILAGE`, `SPOILAGE_ERODES_GAIN`, `CASH_DEADLINE_BINDING`, `NO_STORAGE`, `OFFER_WITHIN_MARGIN`, `OFFER_BELOW_ALTERNATIVES`, `LOW_CONFIDENCE_DEFAULT_TO_REFERENCE`, `NO_RELIABLE_FORECAST`, `SHOCK_SUSPENDS_HOLD`, `DATA_STALE`, `NEIGHBOUR_MARKET_LEADING` (from the cross-mandi feature, optional), `CROP_NOT_HOLDABLE`.

---

## 9. Trigger Engine

### 9.1 Concepts

When the decision is `WAIT_WITH_TRIGGER`, the engine produces a **plan**:
- **Target price** per candidate mandi per day: the observed modal price at which selling there makes `net >= R + margin` after all costs and the spoilage accrued by then.
- **Deadline** `D*`: the last day the plan may run.
- **Fallback** at the deadline: sell at the best available feasible option that day.

### 9.2 Computation

For mandi `m` and plan day `d` (with `h_d = d - as_of`):

```
P_target(m, d) = (R + margin + transport_per_q(m) + fees_per_q + storage_cost_per_q(h_d) + opportunity_cost_per_q(h_d))
                 / ( quality_factor * (1 - weight_loss(h_d)) * (1 - quality_price_discount(h_d)) )
```

(With percentage fees, solve for price accordingly.) `P_target` rises over time because storage and spoilage erode value. The trigger fires when an observation satisfies `modal(m, d) >= P_target(m, d)`.

`margin = decision.trigger_margin_rs` (tuned with the decision parameters).

**Deadline:**
```
latest_safe_day = last day d <= as_of + min(cash_deadline_days, max_storage_days, max(H))
                  such that gain_med(best option at d) >= decision.min_gain_rs
D* = latest_safe_day
```
If the cash deadline is the binding constraint, say so (`CASH_DEADLINE_BINDING`). If spoilage erodes the expected gain before the cash deadline, say so (`SPOILAGE_ERODES_GAIN`).

### 9.3 Daily monitoring loop (`monitor.py`, idempotent)

For each active plan, after each data refresh:
1. Refresh observations. For each monitored mandi require a **fresh, non-suspect** observation (age <= `trigger.max_obs_age_days`, default 2). If none, emit `NO_DATA_ALERT` at most once per plan per `trigger.alert_cooldown_days`, and **do not fire** on stale data.
2. Evaluate the trigger condition per mandi. If `trigger.confirm_obs` (default 1) consecutive qualifying observations are met, mark `TRIGGERED` and record the sale plan: mandi, earliest sale day `>= obs_date + execution_lag_days`.
3. Run the Shock Radar. If `SHOCK` is active for the crop, move to `SUSPENDED_SHOCK` and emit an event. Resume or re-plan when the flag clears.
4. If `D*` is reached or tomorrow is `D*`, emit `DEADLINE_NEAR`, then on `D*` move to `DEADLINE_REACHED` with the fallback recommendation.
5. Re-plan only every `trigger.replan_every_days` (default 3) or when confidence drops a level. Apply hysteresis: a revised target may change by more than `trigger.min_revision_rs` only, to avoid whipsawing the farmer with changing numbers. Emit `PLAN_REVISED`.

Running the monitor twice for the same date must not duplicate events (idempotency key: plan_id + date + event_type).

### 9.4 State machine

| State | Entered when | Exits to |
|---|---|---|
| `PENDING` | Plan created | `ACTIVE` |
| `ACTIVE` | Monitoring | `TRIGGERED`, `DEADLINE_REACHED`, `SUSPENDED_SHOCK`, `CANCELLED` |
| `SUSPENDED_SHOCK` | Radar `SHOCK` for crop | `ACTIVE` (flag clears), `DEADLINE_REACHED`, `CANCELLED` |
| `TRIGGERED` | Price condition met on fresh data | `SOLD` (user confirms), `EXPIRED` (no confirmation after `trigger.confirm_window_days`) |
| `DEADLINE_REACHED` | `D*` reached | `SOLD`, `EXPIRED` |
| `SOLD` | Farmer reports sale | `CLOSED` (receipt generated) |
| `CANCELLED`, `EXPIRED`, `CLOSED` | Terminal | none |

Persist in SQLite (`artifacts/state/triggers.sqlite`) with tables `plans`, `plan_events`, `outcomes`. Provide a schema migration file. Every transition is an append-only event row with timestamp, reason code and data hash.

### 9.5 Events (outbox)

Events: `PLAN_CREATED`, `TRIGGER_FIRED`, `DEADLINE_NEAR`, `DEADLINE_REACHED`, `PLAN_REVISED`, `SHOCK_SUSPENDED`, `SHOCK_CLEARED`, `NO_DATA_ALERT`, `PLAN_CANCELLED`. The API exposes them at `GET /v1/events?since=...`. The interface layer (WhatsApp) polls or subscribes; the ML service never sends messages itself.

### 9.6 Backtest requirements

The backtest must replay triggers day by day (13.3) using only information available each day, including `data_lag_days`, `execution_lag_days` and refit schedule, and must record realised outcomes at the **realised** sale day price.

---
## 10. Confidence labelling (High / Medium / Low)

Confidence is **derived, never invented, never LLM-generated**.

### 10.1 Components (each scored in [0, 1])

| Component | Definition |
|---|---|
| `c_width` | Relative interval width `W = (P90 - P10) / P50` of the calibrated forecast, converted to `1 - percentile_rank(W)` within the validation distribution for the same crop and horizon (narrower = higher) |
| `c_skill` | Trailing skill of M1 vs B0 over the last `confidence.skill_window_days` (default 30) of out-of-sample forecasts for the crop and horizon, clipped to [0, 1] after dividing by `confidence.skill_ref` |
| `c_dq` | Data Quality Score of the (mandi, crop) (4.5) |
| `c_fresh` | 1.0 if the latest usable observation is <= 1 day old, decaying linearly to 0 at `decision.max_obs_age_days` |
| `c_cal` | 1.0 if validation coverage is within tolerance, 0.5 if marginally outside, 0.0 if not |

`score = sum(w_i * c_i)` with weights in config. Labels: `High` if `score >= confidence.t_high`, `Medium` if `score >= confidence.t_med`, else `Low`.

### 10.2 Caps (applied after scoring)

- Active `SHOCK` flag: Low. Active `WATCH`: at most Medium.
- `calib_small`: at most Medium.
- `forecast_usable = false`: Low for any hold-related statement.
- Data Quality Score below `confidence.min_dq` (default 0.5): Low.
- For `h = 0` options with fresh observations, confidence reflects only `c_dq` and `c_fresh`. The price is observed, though still a modal-price proxy (R9).
- For `ACCEPT_OFFER` and `SELL_NOW_NEAREST`, confidence reflects how reliable the comparison against alternatives is. If alternatives could not be assessed reliably (no usable forecast), cap at Medium and add `NO_RELIABLE_FORECAST`.

### 10.3 Validation of labels

`reliability.py` must produce, on validation (and later on test), a table by label: `n`, `win_rate` (share of decisions with realised gain >= 0 vs the reference), `mean_gain`, `loss_rate`, `p10_gain`. Thresholds `t_high` and `t_med` are chosen on validation so that the ordering High > Medium > Low holds for `win_rate`. If it cannot be achieved, set `confidence_validated=false` in `GET /v1/meta` and in every response, and report this in the Calibration Passport. Do not hide non-monotone labels.

---

## 11. Policy-Shock Radar & Crisis Replay

The radar **detects and reacts**. It does not predict policy. Never present it as policy prediction (R11).

### 11.1 Signals

| ID | Signal | Definition |
|---|---|---|
| S1 | Price jump | Robust z-score of 1-, 3- and 7-day log returns at a mandi vs trailing 60-day median/MAD (min `shock.min_obs` observations, default 30) |
| S2 | Breadth | Share of selected mandis for the crop with |z| above `shock.z_thr` and the same sign within a `shock.window_days` window |
| S3 | Activity collapse | Mandi reporting rate or number of reporting mandis drops below `shock.activity_ratio` of its trailing median |
| S4 | Event flag | A row in `events.csv` for the crop or region with `event_date` within `shock.event_window_days` before `as_of` |
| S5 | Model surprise | Realised price fell outside the calibrated P05-P95 for at least `shock.surprise_k` of the last `shock.surprise_n` evaluated forecasts |

### 11.2 Levels

- `NONE`
- `WATCH`: S1 at a single mandi, or S3, or mild S5
- `SHOCK`: S2 breadth >= `shock.breadth_thr` (default 0.4) with |z| >= `shock.z_thr` (default 3), or an S4 event, or severe S5

Clearing requires `shock.clear_days` (default 5) consecutive days without `SHOCK` signals. Use only data available at `as_of` (R2).

### 11.3 Behaviour

- `SHOCK`: hold options (`h > 0`) suspended for the crop; non-hold forecasts widened by `shock.interval_widen` (default 1.5, tuned on validation or synthetic stress only); confidence capped at Low; reason code `SHOCK_SUSPENDED_HOLD`; active plans move to `SUSPENDED_SHOCK`.
- `WATCH`: confidence capped at Medium; `caution_flags += shock_caution`.
- Farmer-facing line (slot-based): "Unusual market movement. Avoid long holds."

### 11.4 `events.csv` (human-filled, empty template)

Columns: `event_id, event_date, crop, region, type, description, source_url, verified_by, verified_on`. Types: `export_policy`, `stock_limit`, `msp_change`, `strike`, `weather_disaster`, `other`. The agent must **not** populate it from memory. It may suggest candidate events with URLs in `DECISIONS.md` for the human to verify.

### 11.5 Crisis Replay data products

Produce `reports/crisis_replay/{episode_id}.{json,md,png}` for each episode:
1. **Real episodes:** windows in the available data where the radar reached `SHOCK` or where the largest absolute moves occurred. If none exist, say so.
2. **Synthetic stress episodes:** use `stress.py` to inject a labelled jump (up or down, parameters in config) into a **copy** of a real series. Label as synthetic on every artifact.
3. **Human-supplied historical events** (for example a verified export restriction) if multi-year data covering it is provided.

Each replay is a day-by-day table: date, observed price, radar level, decision with radar, decision without radar, realised outcome of each. Summary metrics: detection delay (synthetic only, where onset is known), SHOCK days per 100 days in calm periods (false-alarm proxy), and loss avoided or incurred with vs without the radar. Report honestly if the radar did not help.

---

## 12. Regret Receipt

After a plan or decision closes, generate a receipt. Two modes: `real` (farmer reported a sale) and `simulated` (backtest scenario). Simulated receipts carry `is_simulated=true` and the UI must display "SIMULATED".

### 12.1 Computation

Using the same economics (Section 7):
- `actual_net`: net return of what the farmer actually did (mandi, date, price per quintal, quantity), costs from the cost model unless the farmer reported them.
- `reference_net`: realised value of the reference (offer, or nearest-mandi sale on decision day).
- `advice_net`: realised value of following the engine's advice (including trigger replay).
- `oracle_net`: best feasible (mandi, day) in hindsight under the same hard constraints.
- `regret = oracle_net - actual_net`; `advice_gap = advice_net - actual_net`; `reference_gap = reference_net - actual_net`.

### 12.2 Schema

```json
{
  "receipt_id": "...", "plan_id": "...", "mode": "simulated", "is_simulated": true,
  "actual": {"mandi_id": "...", "date": "...", "price_per_q": 1400.0, "net_per_q": 1320.0},
  "reference": {"type": "trader_offer", "net_per_q": 1320.0},
  "advice_followed": {"net_per_q": 1465.0, "mandi_id": "...", "date": "..."},
  "oracle": {"net_per_q": 1520.0, "mandi_id": "...", "date": "..."},
  "gaps_per_q": {"advice_vs_actual": 145.0, "oracle_vs_actual": 200.0},
  "caution_flags": ["modal_price_proxy"]
}
```
(Illustrative numbers only.)

### 12.3 Rules

- Real receipts need a farmer-reported sale; never infer a sale.
- Frame it as learning ("advice would have given about ₹X more per quintal"), never blame or guarantee.
- Store outcomes in `outcomes` for later monitoring (predicted vs realised). **Never** use test-period data for tuning.
- Keep personal data minimal: farmer pseudonymous ID, coarse location, crop, quantities. No phone numbers in the ML service.

---

## 13. Walk-forward backtest

The backtest is the proof. It must be honest, reproducible and leak-free.

### 13.1 Splits

Time-ordered. All forecasts in the evaluation windows come from **rolling-refit models that only saw earlier data** (6.5).

**Default (12-month dev dataset, 2024-08-15 to 2025-08-14):**

| Period | `as_of` range | Purpose |
|---|---|---|
| Warm-up | 2024-08-15 to 2025-01-14 | Feature warm-up and first training windows. No evaluation |
| Validation | 2025-01-15 to 2025-05-10 | Tune decision parameters, confidence thresholds, shock parameters, forecast gating |
| Embargo | 2025-05-11 to 2025-05-31 | At least `max(H)` days so validation outcomes finish before test starts |
| Test | 2025-06-01 to 2025-07-24 | Touched once with `--final` (R4). The last `as_of` is 21 days before the end of data so every outcome is observable |

The warm-up is short for a first refit, so early forecasts will carry `calib_small`. Accept this and report it.

**Auto mode (when longer history is supplied):** test = last `max(20% of span, 60 days)`; validation = preceding 25% of span; embargo = `max(H) + data_lag_days` days between each pair; everything earlier is warm-up. If history >= 2 years, enable calendar-seasonality features and evaluate B1 properly.

### 13.2 Scenario generation (synthetic farmers on real prices)

Use `synth/farmers.py` (4.7). For each crop, sample `backtest.n_farmers_per_crop` (default 200) synthetic farmers per mandi cluster with seeded randomness: village location, `quantity_q`, `vehicle_type`, `cash_deadline_days`, `storage_available` (crop-specific probability from config, flagged as an assumption), `storage_condition`, `quality_factor`. Decision dates: every `backtest.decision_stride_days` (default 2) within the split. Every scenario is a (farmer, crop, as_of) triple.

Trader-offer scenarios: `trader_offer_proxy = nearest_mandi_modal(as_of) * (1 - delta)`, with regimes `delta = 0` (strict), `delta` from `synth.offer_discount` mixture, and a "fixed delta" sweep. Headline results use the **no-offer baseline** (sell at the nearest mandi on `as_of`). Offer-based results are reported per regime and are labelled as proxy results.

### 13.3 Simulation per scenario

1. Build the data snapshot with observations dated <= `as_of - data_lag_days`.
2. Use the model from the latest refit date <= `as_of`.
3. Run the Decision Engine. If the status is `WAIT_WITH_TRIGGER`, create a plan and replay days `as_of + 1 ... D*` using only data available each day (with `data_lag_days`, `execution_lag_days`, shock radar, plan revisions, and `confirm_obs`).
4. Realise the sale at the observed modal price at the chosen mandi on the realised sale day. If no observation exists that day, use the nearest following observed day within `data.target_tolerance_days` (flagged), else **exclude and count** (never impute).
5. Compute realised net with the same economics, including realised spoilage from config (state clearly that spoilage is a modelled quantity, not observed).
6. Store one row per scenario in `artifacts/backtest/{run_id}/scenarios.parquet`.

### 13.4 Policies compared

| ID | Policy | Role |
|---|---|---|
| P0 | Sell now at the nearest mandi | **Headline baseline** |
| P1 | Sell now at the best-net mandi today (spatial choice only, no forecast) | Isolates the value of "where" |
| P2 | Fixed-hold of `N` days (for example 7) at the nearest mandi, if feasible | Naive "wait" strategy |
| P3 | Oracle (perfect foresight within constraints) | Upper bound, for the capture ratio |
| P4 | Engine using B0/B3 baseline forecasts instead of M1 | Shows the value of the model |
| P5 | Engine using point forecast (median only, no risk logic) | Shows the value of uncertainty handling |
| P6 | **Full engine** (M1, conformal, risk rule, trigger, radar) | Product |

### 13.5 Metrics

- **Money:** mean and median realised gain in ₹/quintal vs P0 for each policy; share of scenarios better, equal and worse; loss-rate; mean loss magnitude; P10 and P5 of gain; CVaR(10%) of gain; capture ratio `(P6 - P0) / (P3 - P0)`.
- **Uncertainty:** per crop and horizon: pinball loss, weighted interval score, P50/P80/P90 empirical coverage, mean interval width, skill vs B0, B2, B3 (and B1 where evaluable); reliability of `p_beat` (predicted probability vs realised frequency of beating the reference).
- **Decisions and triggers:** status mix; share of triggers fired vs deadline-reached vs suspended; mean waiting days; realised price vs target; false triggers (fired but later price higher by more than the margin).
- **Slices:** crop, horizon, mandi cluster, cash deadline, confidence label, shock level, month (flagged anecdotal), quantity bucket.

### 13.6 Uncertainty of the backtest itself

Scenarios overlap heavily in time and across farmers. Use a **moving-block bootstrap by decision week** (default block length `backtest.block_weeks` = 2, `backtest.bootstrap_B` = 2000) to produce 95% confidence intervals for mean gain, and report the effective sample size. Report per-crop results separately. Do not pool crops to hide a weak one.

### 13.7 Ablations (on validation first, then reported on test with the same settings)

No weather; no cross-mandi features; no activity proxies; no conformal calibration; no spoilage (to show how much it matters); no radar; point forecast instead of quantiles (P5); baseline forecast instead of M1 (P4); no cash-deadline-aware options; modal price replaced by min-price (a pessimism check on the modal-price proxy). Each ablation reports mean gain and CI vs P6.

### 13.8 "Where we lose money" (mandatory, R7)

`reports/backtest_report.md` must contain a section listing:
- The worst 5% of scenarios and what they share (crop, horizon, mandi, quantity, cash deadline, shock level, confidence label, data quality).
- Root-cause tags per loss: `forecast_miss`, `data_gap`, `stale_obs`, `shock_not_detected`, `spoilage_underestimated`, `transport_assumption`, `trigger_whipsaw`, `deadline_forced_sale`.
- Decision types with negative mean gain.
- Slices where P6 underperforms P0 or P1.
- A plain-language statement of what the engine should **not** be trusted for.

### 13.9 Claim rules (R11)

- A headline claim such as "following the advice earned ₹X more per quintal" is allowed **only** if the test-period 95% bootstrap CI lower bound for P6 minus P0 is above 0, and only with the number, CI, window, scenario count and "synthetic farmers, real prices, modelled spoilage and costs" stated next to it.
- Otherwise the report must say: "No statistically reliable improvement over selling at the nearest mandi in this test window."
- Results from a single 12-month dataset are limited to that window. Season-wise results are single observations per season and must be labelled anecdotal.
- Report numbers produced by the run. Report templates contain **no** hard-coded results.

### 13.10 Test-access control (R4)

`--final` runs are written to `reports/test_access_log.json` with timestamp, git commit, config hash, data hash and operator. Without `--final`, test-period `as_of` dates are masked in loaders (return an error). A second final run requires `--justify "text"` and is logged as such.

---

## 14. Calibration Passport

An auditable artifact proving the uncertainty is honest. Generate for each crop and horizon (and per mandi cluster where n allows):

| Item | Content |
|---|---|
| Coverage table | Empirical coverage at nominal 50%, 80%, 90% with Wilson 95% CI (and effective-n caveat), before and after conformal calibration |
| Reliability plot | Nominal vs empirical coverage |
| PIT histogram | Probability integral transform of realised outcomes under the forecast distribution |
| Sharpness | Mean interval width, relative width |
| Accuracy | Pinball loss and weighted interval score vs B0, B2, B3 (B1 where evaluable) with skill scores |
| Rolling coverage | 30-day rolling coverage over time (to show drift) |
| Confidence reliability | The 10.3 table by label |
| `p_beat` reliability | Calibration curve of predicted probability of beating the reference |
| Forecast gate | `forecast_usable` flag and reason |
| Known weaknesses | Auto-generated text: where coverage fails, where skill is negative, where `calib_small` applies |

**Pass rule:** `|coverage_80 - 0.80| <= calibration.coverage_tolerance` (default 0.07) per crop and horizon on validation. Failures set `forecast_usable=false` (6.8) and are listed prominently.

Outputs: `artifacts/calibration_passport.json`, `reports/calibration_passport.md`, `reports/figures/calibration/*.png`. The passport shows validation numbers by default and test numbers only after a `--final` run, in a separate section.

---
## 15. Interfaces: FastAPI contract and LLM boundary

### 15.1 FastAPI service (`src/sellsmart/api/`)

All responses include a `meta` block: `api_version`, `model_versions`, `config_hash`, `data_hash`, `as_of`, `demo_ready`, `confidence_validated`, `synthetic_inputs`, and `assumptions_register_url`. Validate with pydantic v2. Errors use RFC 7807-style problem JSON. Authentication is out of scope; add a static API key header (`X-API-Key`, env var) for the demo.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness, data freshness per crop, last refit date |
| GET | `/v1/meta` | Versions, `demo_ready`, placeholder-parameter list, confidence validation status, disclaimers |
| POST | `/v1/advice` | Main decision (also covers offer checks: set `trader_offer_per_q`) |
| POST | `/v1/plans` | Create a trigger plan from an `/v1/advice` result (or directly) |
| GET | `/v1/plans/{plan_id}` | Plan state, target prices, deadline, event history |
| POST | `/v1/plans/{plan_id}/cancel` | Cancel |
| POST | `/v1/plans/{plan_id}/outcome` | Record the farmer's actual sale; returns a receipt |
| GET | `/v1/receipts/{receipt_id}` | Regret Receipt |
| POST | `/v1/monitor/run` | Run the daily monitor for a given date (idempotent; also a CLI script) |
| GET | `/v1/events` | Events since a timestamp (outbox for the messaging layer) |
| GET | `/v1/mandis` | Selected mandis per crop with coordinates, confidence of geocode, data quality |
| GET | `/v1/forecast` | Forecast quantiles for (mandi, crop, as_of) for debugging and dashboards |
| GET | `/v1/shock/{crop}` | Current radar level and signals |
| GET | `/v1/calibration/{crop}` | Calibration Passport summary |
| POST | `/v1/resolve-village` | Village text to coordinates with confidence (or clarification request) |

**`POST /v1/advice` request:**
```json
{
  "crop": "onion",
  "quantity_q": 20,
  "village": {"text": "Niphad, Nashik", "lat": null, "lon": null},
  "cash_deadline_days": 7,
  "trader_offer_per_q": 1480,
  "storage_available": true,
  "storage_condition": "on_farm",
  "quality_factor": 1.0,
  "as_of": null,
  "language": "mr"
}
```
`as_of: null` means "latest available data". Units: `quantity_q` is quintals. The backend must reject or ask for clarification on unsupported units. Convert only unambiguous ones (kg, quintal, tonne). "Bags" or "gunny" are ambiguous and require a clarification.

**Response:** the 8.7 payload plus `message` (15.3), `clarification` (nullable) and `meta`.

**Clarification response** (no advice computed): `{"clarification": {"missing": ["village"], "question_id": "ask_village"}}`.

### 15.2 LLM boundary contract (R1)

The LLM sits **outside** the ML service in the interface layer. It has two permitted jobs.

**Job A: parse farmer input into a `ParsedRequest`.**
```json
{
  "crop": "onion|tomato|soybean|null",
  "quantity": 20, "unit": "quintal|kg|tonne|null",
  "village_text": "Niphad",
  "trader_offer_per_q": 1480,
  "cash_deadline_days": 7,
  "language": "mr|hi|en",
  "missing_fields": ["cash_deadline_days"],
  "parse_confidence": 0.0
}
```
The backend validates everything. Crop strings pass through a synonym dictionary first (for example kanda/pyaz/onion; tamatar/tomato; soyabean/soybean). The LLM is a fallback for unrecognised strings. The village is resolved by gazetteer or geocoding with a confidence score. Missing or low-confidence fields trigger the clarification path. Numbers like quantity and offer are never "corrected" by the LLM.

**Job B: phrase the reply.** The backend returns `message = {template_id, language, slots}`. The default and demo-safe path is **template-only**: render `messages.yaml` with slots. If LLM phrasing is enabled, enforce a post-check: every number and mandi name in the LLM output must be in the allowed slot set, no other digits may appear, and the status wording must match. On any violation, discard the LLM text and use the template.

**The LLM must never:** compute or adjust any rupee value, choose a mandi, state a probability, soften or strengthen the recommendation, or invent reasons. It may adapt tone and language only.

### 15.3 Message payload

```json
{
  "template_id": "wait_with_trigger_offer",
  "language": "mr",
  "slots": {"offer": 1480, "days": 6, "mandi": "Lasalgaon", "gain_med": 140,
            "gain_low": 50, "gain_high": 220, "confidence": "Medium",
            "target_price": 1620, "caution": "modal_price_proxy"},
  "text": "<rendered from template>"
}
```
Templates for each status, plus `clarify_*`, `trigger_fired`, `deadline_near`, `shock_suspended`, `no_data_alert`, and `receipt_*`. Every template that shows money shows the **range** and the **confidence label**. Marathi and Hindi templates must be reviewed by a native speaker (`needs_native_review: true` until then). Appendix C has examples.

---

## 16. Testing & leakage guards

Use pytest. CI must run unit, integration, golden and leakage suites. A failing leakage or golden test blocks the phase gate.

### 16.1 Leakage and time

| Test | Assertion |
|---|---|
| Truncation invariance | For 50 random `as_of` dates, features computed from the full dataset equal features computed from data **truncated** to `as_of - data_lag_days`. Any difference means leakage |
| Purge | For every refit, no training row has a target date later than `r - data_lag_days`; calibration rows are strictly later than `train_fit` rows |
| Split order | Validation `as_of` strictly after warm-up; embargo >= `max(H) + data_lag_days`; test after embargo |
| Test masking | Test-period loaders raise without `--final` |
| Neighbour selection | Top-k neighbour sets are computed from training rows only |
| Event flags | Event features use `event_date <= as_of` only |
| Trigger replay | Replay on day `d` never reads observations dated after `d - data_lag_days` |

### 16.2 Data and synthetic separation

- Feature list and synthetic column list are disjoint (4.7).
- Synthetic output rows always have `is_synthetic=True`, `generator`, `seed`, `config_hash`.
- No synthetic value appears in any forecast target or training row.
- Cleaning: duplicates, `inconsistent_minmax`, outlier flags, commodity regex (`Soyabean` and `Soybean` both map to soybean), alias handling for district names (Ahmednagar/Ahilyanagar and similar).
- Maharashtra filter produces the review file and flags ambiguous district names.

### 16.3 Economics invariants

- `net` is strictly increasing in price and non-increasing in `h` when forecast prices are held constant.
- Transport: `trips = ceil(qty / capacity)`; per-quintal cost is non-increasing in quantity within one vehicle type; a doubling of distance never reduces cost.
- Units: ₹ per original quintal; a test with known inputs checks numeric results by hand-computed fixtures.
- Plausibility guard fires for an intentionally absurd transport rate fixture.
- `PLACEHOLDER` parameters force `demo_ready=false` and the warning banner.
- Hard constraints: no option violates cash deadline, storage availability or `max_storage_days`.

### 16.4 Forecasting and calibration

- Quantile outputs are non-crossing after the fix, and the fix count is reported.
- Conformal: on a synthetic exchangeable fixture, empirical coverage of the calibrated 80% interval is within tolerance.
- Baselines B0 and B3 reproduce hand-computed values on small fixtures.
- B1 returns `n/a` (not NaN) when no year-ago value exists.
- Seeds: two runs with identical config and data produce identical forecasts (hash equality).

### 16.5 Decision and trigger golden fixtures (synthetic, deterministic)

| Fixture | Expected |
|---|---|
| Steadily rising price series, holdable crop, loose deadline | `WAIT_WITH_TRIGGER` |
| Falling series | `SELL_NOW_NEAREST` or `ACCEPT_OFFER` |
| Flat series | `ACCEPT_OFFER` / `SELL_NOW_NEAREST`, never `WAIT` |
| Shock series (injected jump) | Hold suspended, `SHOCK_SUSPENDED_HOLD`, confidence Low |
| Cash deadline 0 | Only `h = 0` options |
| No storage | Only `h = 0` options |
| Stale data | `DATA_STALE`, no trigger fires |
| Tomato with realistic spoilage config | Hold options infeasible or non-beneficial |

State-machine tests cover every transition in 9.4, idempotent monitor runs, and event de-duplication.

### 16.6 LLM boundary and API

- A message with an extra digit not in the slots is rejected and replaced by the template.
- `ParsedRequest` fuzz tests: Marathi, Hindi, Hinglish and code-mixed strings; ambiguous units trigger clarification.
- API schema and contract tests (OpenAPI), error handling, `meta` fields present on every response, `demo_ready` correct.

---

## 17. Optional modules (do not start until Section 19 core criteria pass)

| Module | Status | Spec (stub) |
|---|---|---|
| **FPO Splitter** | **Secondary** (the hackathon brief lists an FPO bulk mode, so build it right after core acceptance) | Linear program: variables `x[v, m]` quintals from village group `v` to mandi `m`. Maximise `sum x[v,m] * E[net(v, m, h)]` minus a price-impact penalty `impact_coef * (sum_v x[v,m])^2 / absorb_cap[m]` (convex, solve with `scipy.optimize` or cvxpy). Constraints: supply per village, truck capacities, cash deadlines, `absorb_cap[m]`. **`absorb_cap` and `impact_coef` are assumptions** (arrivals data is unavailable); mark them `PLACEHOLDER` and disclose. Output allocation table, projected ₹ vs sending everything to the nearest mandi, and sensitivity to the impact assumption. Expose via `POST /v1/fpo/allocate` |
| Anti-Herd Dispatch | Optional wow module | A notebook-level simulation: if a fraction of nearby farmers all follow the same advice, how much does the target mandi's price move? Use only elasticity parameters grounded in the data or marked as assumptions. Never used in core claims |
| Photo-to-Shelf-Life | Only if time (tomato) | Image classifier for ripeness or shelf life, evaluated on real unaugmented photos. Feeds `quality_factor`. Out of scope until a labelled dataset exists |
| Lead-lag graph | **Cut** as a product | Already used as the neighbour features and the optional reason code `NEIGHBOUR_MARKET_LEADING` |
| Truck pool matcher | Cut (fold into FPO Splitter) | Needs coordination the prototype cannot test |
| Satellite radar | Cut | Unverified value, high risk |
| User risk dial | Cut | Use `risk_mode = balanced`; the parameter exists in config for sensitivity analysis only |

---

## 18. Build phases

Each phase ends with passing tests, artifacts in `reports/` or `artifacts/`, and an entry in `docs/DECISIONS.md`. Do not proceed if a phase gate fails. If it cannot be passed, record why and stop to ask the human.

| Phase | Work | Deliverables | Gate |
|---|---|---|---|
| **0 Bootstrap** | Repo layout, config loader, manifest, logging, disclaimers module, CI, test scaffolding | Skeleton runs; empty tests pass | `pytest` green; manifest records config and data hashes |
| **1 Data audit and cleaning** | Run the Appendix D audit; Kaggle ingestor; canonicalisation; Maharashtra filter review file; commodity/variety proposal (**stop for human confirm**); mandi selection report; geocoding | `reports/data_audit.md`, `reports/maharashtra_filter_review.csv`, `config/commodity_map.yaml`, `reports/mandi_selection_report.md`, `config/mandis.yaml` | Date range and mandi counts per crop verified; ambiguity list reviewed or fallback logged; **risk gate: if fewer than 6 usable mandis for a crop, report and decide with the human whether to continue** |
| **2 Gold panel and features** | Calendar inference, gap handling, DQ score, feature builder, leakage guard, suspect-outlier handling | `data/gold/*.parquet`, `reports/feature_report.md` | Truncation-invariance and purge tests pass |
| **3 Baselines and eval harness** | B0-B3, metrics, rolling splits, test masking | `reports/baseline_report.md` | Metrics reproduce hand-computed fixtures; B1 `n/a` handled |
| **4 Quantile models and calibration** | M1, rolling refit with trailing calibration, CQR, gating, Calibration Passport v1 (validation) | `artifacts/models/`, `artifacts/forecast_gates.json`, `reports/calibration_passport.md` | Coverage check run; gates computed; no test data touched |
| **5 Economics** | Spoilage, transport (trip-based), storage, fees, source registry, plausibility guard, assumptions register | `docs/assumptions_register.md`, economics unit tests | Invariants pass; PLACEHOLDER detection works |
| **6 Decision Engine and confidence** | Options, net distributions, reference, rule, tuning on validation, confidence labels, reliability table | `artifacts/decision_params.json`, `reports/tuning_grid.csv`, `reports/confidence_reliability.md` | Golden fixtures pass; hard constraints never violated |
| **7 Trigger Engine** | Targets, deadline, monitor, state machine, SQLite store, events | `artifacts/state/triggers.sqlite` schema, monitor CLI | State-machine and idempotency tests pass |
| **8 Scenarios and backtest (validation)** | Synthetic farmers, simulation with replay, policies P0-P6, ablations, loss analysis | `reports/backtest_validation_report.md` | Reproducible runs; exclusions counted; "Where we lose money" present |
| **9 Shock Radar, Crisis Replay, Regret Receipt** | Radar signals and behaviour, stress tests, replay products, receipts | `reports/crisis_replay/*`, receipt generator | Golden shock fixture passes; synthetic episodes labelled |
| **10 API and LLM contract** | FastAPI endpoints, schemas, message templates, number check, village resolver | OpenAPI doc, contract tests | API tests pass; `meta` on all responses |
| **11 Final test run and reports** | Freeze parameters, run `--final` once, generate backtest report and Calibration Passport (test section), README | `reports/backtest_report.md`, `reports/test_access_log.json` | Section 19 criteria evaluated and written up |
| **12 (Secondary) FPO Splitter** | Section 17 spec | `POST /v1/fpo/allocate`, report | Only after Phase 11 |

### 18.1 Minimum viable subset (if time is very limited, such as a 12-hour hackathon)

Keep the **order** and the **rules**, shrink the **scope**:
1. Phase 1 on the dev dataset, with one or two crops first (onion, then tomato), and only the mandis that pass the quality gate.
2. Phase 2 and 3 with B0 and B3 only, and a smaller feature set (own lags, regional median, activity proxies).
3. Phase 4 with M1 at horizons {7, 14} and CQR on the (0.10, 0.90) pair only.
4. Phase 5 with trip-based transport and one spoilage curve per crop (parameters PLACEHOLDER, flagged).
5. Phase 6 with a coarse grid for tuning.
6. Phase 8 with fewer farmers (for example 30 per crop) and stride 4, producing P0, P1, P3, P6.
7. Phase 10 with `/v1/advice` only and template messages.

Do not cut: the leakage tests, the validation/test separation, the "Where we lose money" section, and the PLACEHOLDER warning. These are the credibility. Do not hard-code a headline number in the pitch. Use the number the run produced.

---

## 19. Acceptance criteria

The project is **accepted** when all items below are true, or when each unmet item is explicitly documented with a reason (some depend on data the human must supply).

### 19.1 Data
- [ ] `reports/data_audit.md` states date range, rows per crop, and distinct dates per selected mandi.
- [ ] Maharashtra filter review file exists and ambiguous names were reviewed or the fallback is logged.
- [ ] Mandi selection report lists kept and rejected mandis with reasons. If fewer than 10 per crop qualified, this is stated.
- [ ] All selected mandis have `geocode_confidence` recorded; none were invented.

### 19.2 Forecasting
- [ ] Walk-forward forecasts exist for every crop and horizon in H for validation (and test after `--final`).
- [ ] Baselines B0, B2, B3 reported; B1 reported where evaluable, otherwise `n/a (insufficient history)`.
- [ ] Calibration Passport generated. For each crop and horizon, P80 coverage is within `calibration.coverage_tolerance`, **or** the combination is flagged `forecast_usable=false`.
- [ ] Quantile crossing counts reported.

### 19.3 Decision, trigger, confidence
- [ ] All golden fixtures pass. Hard constraints are never violated in any backtest scenario (asserted in code).
- [ ] Decision parameters were tuned on validation only and frozen in `decision_params.json` before the final run.
- [ ] Confidence reliability table exists. Either ordering holds or `confidence_validated=false` is surfaced in API output.
- [ ] Trigger replay runs end to end; state machine tests and idempotency tests pass.

### 19.4 Backtest and claims
- [ ] The test period was accessed once with `--final`, logged in `test_access_log.json`.
- [ ] The report includes P0-P6, per-crop results, 95% block-bootstrap CIs, scenario counts, exclusions, and the "Where we lose money" section.
- [ ] Ablations reported.
- [ ] Any headline claim satisfies the 13.9 rule. If the CI includes zero, the report says so.
- [ ] Synthetic inputs are disclosed in every report and API response that uses them.

### 19.5 Economics and honesty
- [ ] `docs/assumptions_register.md` lists every PLACEHOLDER or unverified parameter. If any remain, `demo_ready=false` and the warning banner shows everywhere.
- [ ] Transport plausibility guard has run, and its output is reviewed by a human.
- [ ] No output claims guaranteed profit, exact prices or policy prediction.

### 19.6 Engineering
- [ ] Two runs with the same config and data produce identical artifacts (hash check).
- [ ] API contract tests pass; `meta` is present on every response.
- [ ] The LLM boundary tests pass: no number in a final message outside the slots.
- [ ] `README.md` explains setup, commands per phase, and how to reproduce reports.

---

## 20. Reports, artifacts and run manifest

| Path | Content |
|---|---|
| `reports/data_audit.md` | Date range, rows, distinct dates, per-mandi coverage, naming variants |
| `reports/maharashtra_filter_review.csv` | Ambiguous district/market rows |
| `reports/mandi_selection_report.md` | Kept and rejected mandis with reasons |
| `reports/baseline_report.md`, `reports/feature_report.md` | Baseline metrics; feature summaries and leakage test results |
| `reports/calibration_passport.md` | Section 14 |
| `reports/tuning_grid.csv`, `reports/confidence_reliability.md` | Section 8.6, 10.3 |
| `reports/backtest_validation_report.md`, `reports/backtest_report.md` | Validation and final test reports |
| `reports/crisis_replay/*` | Section 11.5 |
| `reports/test_access_log.json` | Test-access log |
| `reports/figures/*` | Plots (PNG) |
| `artifacts/models/`, `artifacts/forecast_gates.json`, `artifacts/decision_params.json` | Frozen models and parameters |
| `artifacts/state/triggers.sqlite` | Plans, events, outcomes |
| `artifacts/backtest/{run_id}/` | Scenarios parquet, metrics JSON, manifest |
| `docs/DECISIONS.md`, `docs/assumptions_register.md` | Decision log; assumptions |

**Run manifest** (`manifest.json` per run): `run_id`, `started_at`, `git_commit`, `config_hash`, `data_hash` (per stage), `seeds`, `package_versions`, `row_counts`, `min_date`, `max_date`, `demo_ready`, `placeholder_params`, `synthetic_generators`, `final_test_run` (bool).

Every generated report starts with a header showing: `demo_ready`, synthetic-input box, data window, and the modal-price-proxy statement (R9).

---

## 21. Risks, assumptions and open items for the human

### 21.1 Known risks

| Risk | Impact | Mitigation in this PRD |
|---|---|---|
| Only 12 months of history | No seasonal baseline, no season-wise robustness, short test window | Calendar features off; B1 `n/a`; anecdotal labelling; human supplies longer history (CEDA or similar, unverified) |
| No arrivals data | Weaker oversupply signal | Activity proxies labelled as proxies; dormant arrivals path |
| Modal price is a proxy | Farmer's realised price differs (grade, bargaining, deductions) | R9 flag on every output; min-price ablation |
| Trader offers are not in the data | Cannot replay real offers | Offer proxy with delta regimes; headline uses no-offer baseline |
| Spoilage and fee parameters unverified | Hold advice can be wrong | Source registry, PLACEHOLDER rule, sensitivity analysis |
| Transport costs unverified | Switch/hold advice can flip | Trip-based model, plausibility guard, sensitivity |
| Policy shocks (export bans and similar) | Large unpredictable losses | Radar reacts only; hold suspended; Low confidence; honest messaging |
| Small data, small test window | Wide CIs; claims may not be provable | CI-based claim rule; per-crop reporting |
| Dataset has no State column | Misassigned mandis | Review file, geocode checks |
| Stale dev data (ends Aug 2025) | Cannot run live | API ingestor for live path; daily log from now on |
| Marathi/Hindi message quality | Mistranslation | Native-speaker review flag |
| Ethical risk of bad advice to small farmers | Real financial harm | Decision-support wording, conservative defaults, no guaranteed claims, human review before any real-user use |

### 21.2 Open items only the human can resolve

1. Supply or approve the data (and a longer history file if available). Confirm the licence terms of each source.
2. Verify the live data.gov.in endpoint, key requirement and rate limits (marked UNVERIFIED).
3. Confirm the commodity/variety mapping in `commodity_map.yaml`.
4. Verify spoilage, storage, fee and transport parameters and replace PLACEHOLDER sources.
5. Provide `events.csv` entries with verified sources.
6. Native-speaker review of Marathi and Hindi templates.
7. Decide the pitch wording once the backtest numbers exist.

### 21.3 Assumptions (all must appear in `assumptions_register.md`)

`data_lag_days`, `execution_lag_days`, synthetic village distance range, quantity choices, cash-deadline weights, storage availability probabilities, offer-discount regimes, `max_haul_km`, `road_factor`, vehicle capacities and rates, holding-rate, shock thresholds, FPO `absorb_cap` and `impact_coef`.

---
## Appendix A: `config/default.yaml`

Values marked `# ASSUMPTION` or `# HUMAN` are placeholders for human review and must be listed in `docs/assumptions_register.md`. Values marked `# INITIAL` are starting points that tuning on validation may replace (and the chosen values are then frozen in `artifacts/decision_params.json`).

```yaml
project: {name: sell_smart, seed: 20261003, timezone: Asia/Kolkata}

time:
  data_lag_days: 1            # ASSUMPTION, UNVERIFIED reporting delay
  execution_lag_days: 1       # ASSUMPTION

data:
  max_ffill_days: 3
  target_tolerance_days: 0    # 1 allowed, flagged
  primary_source: kaggle_agmarknet_oct24_aug25
  live_source: datagov_api    # needs env DATAGOV_API_KEY; UNVERIFIED endpoint details

quality:
  outlier_k: 6
  max_unparseable_date_rate: 0.001
  dq_weights: {coverage_90d: 0.4, gap_penalty: 0.2, recency: 0.2, one_minus_suspect_rate: 0.2}

calendar: {open_threshold: 0.5}

mandi_select:                 # INITIAL, human may adjust after the audit
  target_min: 10
  target_max: 15
  min_coverage: 0.80
  max_gap_days: 14
  recency_days: 30
  max_radius_km: 150
  demo_region: Nashik

features:
  lags: [1, 2, 3, 7, 14, 21, 28]
  rolling_windows: [7, 14, 28]
  neighbour_k: 3
  calendar_min_years: 2
  use_weather: false
  use_activity_proxies: true
  use_cross_mandi: true

splits:
  mode: explicit              # explicit | auto
  warmup_end: 2025-01-14
  val_start: 2025-01-15
  val_end: 2025-05-10
  embargo_end: 2025-05-31
  test_start: 2025-06-01
  test_end_asof: 2025-07-24
  auto: {test_frac: 0.20, test_min_days: 60, val_frac: 0.25}

forecast:
  horizons: [1, 3, 7, 10, 14, 21]
  quantiles: [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
  refit_days: 14
  min_skill: 0.0
  inner_val_tail_frac: 0.15
  lgbm: {num_leaves: 15, min_data_in_leaf: 40, learning_rate: 0.05, feature_fraction: 0.8,
         lambda_l2: 5.0, n_estimators: 600, early_stopping_rounds: 40}

conformal:
  calib_days: 45
  min_calib_n: 100
  small_sample_inflation: 1.25
  pairs: [[0.25, 0.75], [0.10, 0.90], [0.05, 0.95]]

calibration: {coverage_tolerance: 0.07, nominal_levels: [0.5, 0.8, 0.9]}

economics:
  road_factor: 1.3                      # ASSUMPTION haversine fallback
  round_trip_factor: 2.0                # ASSUMPTION
  transport_plausible_range: [null, null]   # HUMAN: Rs per quintal per km band
  transport_max_share_of_price: 0.15    # ASSUMPTION warning threshold
  holding_rate_per_day: 0.0             # HUMAN
  sensitivity_pct: 0.25
  trader_offer_known_deductions_per_q: 0.0  # ASSUMPTION

decision:
  risk_mode: balanced
  lambda: {cautious: 1.0, balanced: 0.5, aggressive: 0.2}
  risk_quantile: 0.10
  p_min: 0.70                 # INITIAL, tuned on validation
  min_gain_rs: 30             # INITIAL, tuned
  lb_margin_rs: 0             # INITIAL, tuned
  trigger_margin_rs: 10       # INITIAL, tuned
  max_haul_km: 120            # ASSUMPTION
  max_obs_age_days: 3
  default_cash_deadline_days: 7   # ASSUMPTION, flagged deadline_assumed

tuning:
  grid:
    p_min: [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
    min_gain_rs: [0, 15, 30, 50, 75]
    lb_margin_rs: [-50, -25, 0, 25]
    lambda: [0.2, 0.5, 1.0]
  max_loss_rate: 0.35         # HUMAN policy choice
  min_p10_gain: -100          # HUMAN policy choice, Rs/quintal

trigger:
  max_obs_age_days: 2
  alert_cooldown_days: 3
  confirm_obs: 1
  replan_every_days: 3
  min_revision_rs: 15
  confirm_window_days: 3

confidence:
  weights: {c_width: 0.25, c_skill: 0.25, c_dq: 0.2, c_fresh: 0.15, c_cal: 0.15}
  t_high: 0.75                # INITIAL, tuned for monotone reliability
  t_med: 0.50                 # INITIAL, tuned
  skill_window_days: 30
  skill_ref: 0.10
  min_dq: 0.5

shock:
  min_obs: 30
  z_thr: 3.0
  window_days: 3
  breadth_thr: 0.4
  activity_ratio: 0.5
  event_window_days: 14
  surprise_k: 3
  surprise_n: 10
  clear_days: 5
  interval_widen: 1.5         # ASSUMPTION, check on synthetic stress only

synth:
  village_km_min: 5           # ASSUMPTION
  village_km_max: 40          # ASSUMPTION
  quantity_choices: [10, 20, 50, 100]
  cash_deadline: {values: [0, 3, 7, 14, 21], weights: [0.2, 0.25, 0.25, 0.2, 0.1]}   # ASSUMPTION
  storage_available_prob: {onion: 0.6, tomato: 0.3, soybean: 0.8}                   # ASSUMPTION
  offer_discount:
    regimes:
      strict: {delta: 0.0}
      mixture: {deltas: [0.0, 0.05, 0.10, 0.15], weights: [0.25, 0.25, 0.25, 0.25]}
  quality_factor: {mean: 1.0, sd: 0.03, min: 0.9, max: 1.0}                          # ASSUMPTION

backtest:
  n_farmers_per_crop: 200
  decision_stride_days: 2
  fixed_hold_days: 7
  block_weeks: 2
  bootstrap_B: 2000

api: {key_env: SELLSMART_API_KEY, language_default: mr}
```

---

## Appendix B: `config/crops.yaml` skeleton (every value is a PLACEHOLDER)

The numbers below are **illustrative, not sourced**. They exist only so the pipeline can run in development. Every one carries `source: PLACEHOLDER`, so `demo_ready=false` until a human replaces them with verified, cited values (R6).

```yaml
sources: {}     # SRC_xxx entries: {citation, url, retrieved, verified_by}

crops:
  onion:
    hold_allowed_default: true
    max_storage_days: {on_farm: 45, ventilated: 90, cold: 150}      # source: PLACEHOLDER
    weight_loss:   {lambda: 120.0, beta: 1.3, source: PLACEHOLDER}
    quality_discount: {lambda: 150.0, beta: 1.5, source: PLACEHOLDER}
    storage_multiplier: {on_farm: 1.0, ventilated: 0.7, cold: 0.4}  # source: PLACEHOLDER
    storage_cost_per_q_day: {on_farm: 0.0, ventilated: 0.5, cold: 2.0}  # source: PLACEHOLDER
  tomato:
    hold_allowed_default: false
    max_storage_days: {on_farm: 3, ventilated: 6, cold: 14}         # source: PLACEHOLDER
    weight_loss:   {lambda: 15.0, beta: 1.6, source: PLACEHOLDER}
    quality_discount: {lambda: 8.0, beta: 1.8, source: PLACEHOLDER}
    storage_multiplier: {on_farm: 1.0, ventilated: 0.8, cold: 0.4}  # source: PLACEHOLDER
    storage_cost_per_q_day: {on_farm: 0.0, ventilated: 1.0, cold: 4.0}  # source: PLACEHOLDER
  soybean:
    hold_allowed_default: true
    max_storage_days: {on_farm: 120, ventilated: 180, cold: 270}    # source: PLACEHOLDER
    weight_loss:   {lambda: 900.0, beta: 1.2, source: PLACEHOLDER}
    quality_discount: {lambda: 400.0, beta: 1.4, source: PLACEHOLDER}
    storage_multiplier: {on_farm: 1.0, ventilated: 0.8, cold: 0.5}  # source: PLACEHOLDER
    storage_cost_per_q_day: {on_farm: 0.0, ventilated: 0.3, cold: 1.0}  # source: PLACEHOLDER

transport:
  vehicles:                                  # per-trip costs, source: PLACEHOLDER
    - {name: small_pickup, capacity_q: 15,  fixed_cost: 150, rate_per_km: 14.0, loading_cost: 100}
    - {name: tempo,        capacity_q: 40,  fixed_cost: 250, rate_per_km: 18.0, loading_cost: 200}
    - {name: truck,        capacity_q: 150, fixed_cost: 500, rate_per_km: 28.0, loading_cost: 500}

fees:
  default: {commission_pct: 0.0, market_fee_pct: 0.0, hamali_per_q: 0.0, weighing_per_q: 0.0,
            paid_by: {commission: seller, market_fee: buyer, hamali: seller, weighing: seller}}   # source: PLACEHOLDER
  per_mandi: {}                              # overrides keyed by mandi_id
```

---

## Appendix C: `config/messages.yaml` examples

Slots are filled by code. Marathi and Hindi text must be reviewed by a native speaker before any real use (`needs_native_review: true`). English text is the reference meaning.

```yaml
wait_with_trigger_offer:
  needs_native_review: true
  en: "Trader offer: Rs {offer}/quintal. Hold {days} days and sell at {mandi}. Typical gain Rs {gain_med}/quintal (likely range {gain_low} to {gain_high}). Sell earlier if price reaches Rs {target_price}. Confidence: {confidence}."
  mr: "व्यापाऱ्याची ऑफर ₹{offer}/क्विंटल आहे. {days} दिवस थांबा आणि {mandi} येथे विका. अपेक्षित फायदा ₹{gain_med}/क्विंटल (शक्यता ₹{gain_low} ते ₹{gain_high}). भाव ₹{target_price} झाल्यास लगेच विका. विश्वास: {confidence}."
  hi: "व्यापारी का ऑफर ₹{offer}/क्विंटल है। {days} दिन रुकें और {mandi} में बेचें। अपेक्षित फायदा ₹{gain_med}/क्विंटल (संभावित ₹{gain_low} से ₹{gain_high})। भाव ₹{target_price} होने पर तुरंत बेचें। भरोसा: {confidence}।"

accept_offer:
  needs_native_review: true
  en: "The trader's offer of Rs {offer}/quintal is close to the best option we found. Selling now looks reasonable. Confidence: {confidence}."
  mr: "व्यापाऱ्याची ₹{offer}/क्विंटल ऑफर आमच्या शोधातील सर्वोत्तम पर्यायाच्या जवळ आहे. आता विकणे योग्य दिसते. विश्वास: {confidence}."
  hi: "व्यापारी का ₹{offer}/क्विंटल का ऑफर हमारे मिले सबसे अच्छे विकल्प के करीब है। अभी बेचना ठीक लगता है। भरोसा: {confidence}।"

switch_market_now:
  needs_native_review: true
  en: "Selling at {mandi} today gives about Rs {net}/quintal after transport, which is Rs {gain_med}/quintal more than {reference_label}. Confidence: {confidence}."

trigger_fired:
  needs_native_review: true
  en: "Price at {mandi} reached Rs {price}/quintal. This is a good time to sell."

deadline_near:
  needs_native_review: true
  en: "Your plan ends tomorrow. Best option now: {mandi}, about Rs {net}/quintal."

shock_suspended:
  needs_native_review: true
  en: "Unusual market movement. Avoid long holds. Please compare offers before selling."

clarify_village:
  needs_native_review: true
  en: "Which village or taluka are you in?"

clarify_deadline:
  needs_native_review: true
  en: "When do you need the money? Today, within 3 days, within a week, or later?"

footer_proxy:
  en: "Based on market (modal) prices. Your actual price may differ."
```

---

## Appendix D: Templates and the first audit step

### D.1 Data audit script (run first in Phase 1)

The dev dataset has no State column and uses the date format `05 Apr 2025`. Adapt column names if the file differs.

```python
import pandas as pd

df = pd.read_csv("data/raw/agmarknet_oct24_aug25.csv")
df["date"] = pd.to_datetime(df["Price Date"], format="%d %b %Y", errors="coerce")
print("unparseable dates:", df["date"].isna().mean())
print("date range:", df["date"].min(), df["date"].max(), "distinct days:", df["date"].nunique())

crops = df[df["Commodity"].str.contains("Onion|Tomato|Soyabean|Soybean", case=False, na=False)]
print(sorted(crops["Commodity"].unique()))
print(crops.groupby("Commodity")["Variety"].value_counts().head(60))

mh_districts = ["Nashik", "Pune", "Latur", "Akola", "Ahmednagar", "Ahilyanagar", "Solapur",
                "Satara", "Sangli", "Kolhapur", "Jalgaon", "Dhule", "Aurangabad",
                "Chhatrapati Sambhajinagar", "Osmanabad", "Dharashiv", "Amravati", "Nagpur",
                "Wardha", "Buldhana", "Yavatmal", "Beed", "Jalna", "Parbhani", "Nanded"]
mh = crops[crops["District Name"].isin(mh_districts)]
print(mh.groupby(["Commodity", "District Name", "Market Name"])["date"].agg(["min", "max", "nunique"]))
```
Key output: distinct dates per mandi (about 365 would be ideal; under about 250 means a gappy series). Remember that `Aurangabad` and similar names exist in other states, so verify by geocoding before accepting a market as Maharashtra.

### D.2 `docs/DECISIONS.md` entry template

```markdown
## YYYY-MM-DD  Phase N  Short title
- Context: what was ambiguous or needed deciding
- Options considered:
- Decision and reason:
- Verified or UNVERIFIED facts used (with URLs):
- Impact on results / assumptions register:
```

### D.3 `docs/assumptions_register.md` template (auto-generated)

| Parameter | Value | Unit | Source status | Used in | Sensitivity (decision flip rate at +/-25%) | Owner to verify |
|---|---|---|---|---|---|---|

---

## Appendix E: Glossary

| Term | Meaning |
|---|---|
| Mandi | Regulated wholesale agricultural market (APMC) |
| FPO | Farmer Producer Organisation |
| Quintal | 100 kg |
| Modal price | Most common transaction price at a mandi on a day. A market-level proxy, not an individual farmer's price |
| Reference (`R`) | The value against which gains are measured: trader offer, or nearest-mandi sale today |
| `as_of` | Decision date |
| Net return | ₹ per original quintal after transport, fees, storage, spoilage and opportunity cost |
| Trigger plan | Target price per mandi and day plus deadline and fallback |
| CQR | Conformalized quantile regression |
| WIS | Weighted interval score |
| PIT | Probability integral transform |
| Capture ratio | Share of the oracle's improvement over the baseline that the engine achieved |
| Embargo | Gap between periods so outcomes of one do not overlap the next |
| `demo_ready` | Boolean: false if any economic parameter is PLACEHOLDER or unverified |
