# Architecture & Engineering Decisions (ADR)

## ADR-001: Synthetic Price Series for Perishables (Onion & Tomato)

### Status
Accepted (Human Decision under Time Constraint)

### Context & Decision
The Sell Smart PRD Section 4.7 Rule 3 and Rule R5 state that price observations must come from verified Agmarknet trading records, forbidding synthetic prices for primary evaluation.

However, during prototype development under severe hackathon time constraints, historical Agmarknet records available in the local offline Kaggle archive (`ML/archive/agmarknet-india-commodity-prices-2024-2025/agmarknet_india_historical_prices_2024_2025.csv`) only contained comprehensive, verified 365-day coverage for **Soybean** (Madhya Pradesh mandis). Onion and Tomato lacked complete, unbroken 12-month daily records in the offline archive.

**Decision**:
> **"Onion and tomato price series are synthetic by human decision (time constraint). Soybean uses real Agmarknet data."**

### Data Provenance & Source Tagging
Every price record across Bronze, Silver, and Gold datasets, as well as downstream feature panels and decision outputs, must be explicitly tagged:
- **Soybean**:
  - `price_source: "real"`
  - `is_synthetic: false`
  - Provenance: Agmarknet India Historical Commodity Prices 2024–2025.
- **Onion**:
  - `price_source: "synthetic"`
  - `is_synthetic: true`
  - Provenance: Aligned synthetic daily series modeled after Lasalgaon / Pimpalgaon seasonality.
- **Tomato**:
  - `price_source: "synthetic"`
  - `is_synthetic: true`
  - Provenance: Aligned synthetic daily series modeled after Nashik / Pimpalgaon perishability.

### Operational Constraints & Guardrails
1. **Per-Crop Flagging in Every Response**: Every report header and every `/v1/advice` API response payload MUST carry `price_source` ("real" | "synthetic") and `is_synthetic` (true | false).
2. **Prominent Visible Disclosure**: Any advice response or report involving Onion or Tomato MUST visibly disclose:
   > `[SIMULATED PRICES] Onion/Tomato price series are synthetic by human decision (time constraint). Prices and price movements are simulated.`
3. **Headline ₹ Claims Restriction**:
   > **Antigravity Rule: Headline ₹ claims are allowed ONLY for crops with real prices (`price_source == "real"`).**
   - For synthetic crops (Onion and Tomato), promotional or headline realization claims (e.g., "+₹90/quintal profit gain") are **STRICTLY PROHIBITED**.
   - Net return estimates for synthetic crops must be labeled as illustrative benchmark simulations, not guaranteed economic claims.

## ADR-002: Forecast Usability Gating, Conformal Coverage Diagnosis, and Baseline B3 Protocol

### Status
Accepted (Strict PRD Compliance)

### 1. Gating Period & Test Set Access Disclosure
- **Validation-Only Gating**: Per PRD §6.8, usability gating for all crops and horizons is evaluated strictly on the **validation period** ($T_{\text{val}} = \text{2025-04-27}$ to $\text{2025-06-21}$) with a 21-day embargo ($\max(H) = 21\text{d}$).
- **Test Set Access Disclosure**: The test period ($T_{\text{test}} = \text{2025-06-21}$ to $\text{2025-08-14}$) was accessed and viewed during earlier prototype runs, as logged in `reports/test_access_log.json` (758 entries). All subsequent parameter tuning, conformal margin calibration, and forecast usability gate decisions are strictly computed on the validation period only.

### 2. Coverage Diagnosis by Split and Calendar Month (Soybean)
- **Calibration Set (Trailing 45d of Train, Mar 14 – Apr 27, 2025)**: P80 Empirical Coverage = **78.9% – 81.9%** (nominal 80%).
- **Validation Set (Apr 27 – Jun 21, 2025)**: P80 Empirical Coverage with CQR = **81.0% – 82.4%** (comfortably within $|80\% \pm 7\%|$ tolerance).
- **Test Set (Static Unrefit, Jun 21 – Aug 14, 2025)**: P80 Empirical Coverage drops to **58.6% – 32.7%** due to unrefit distribution shift.
- **Monthly Breakdown**:
  - 2024-08 to 2025-06 (11 months): Stable coverage between **77.2% and 87.1%**.
  - 2025-07: Drops to **61.9%** (H=1d) / **19.2%** (H=21d).
  - 2025-08: Drops to **30.3%** (H=1d).
  - **Root Cause**: Seasonal Kharif onset and pre-sowing price acceleration in July–August. Static models trained up to April 2025 fail to extrapolate level price increases without rolling refits.

### 3. Distribution Shift Remediation Hierarchy (PRD §6.5)
1. **Rolling Refit with Trailing Calibration (PRD §6.5)**: Refitting every 14 days with trailing 45-day calibration restores validation P80 coverage to **84.6% – 89.6%**, beating $B_0$ by **+31.4% to +54.5%** and $B_3$ by **+3.5% to +30.8%**.
2. **Volatility-Normalized Conformal Scores**: Scaling non-conformity scores by $\sigma_t = \max(\text{roll\_std\_14d}, 10.0)$ achieves **85.5%** P80 coverage on validation.
3. **Gate Threshold Invariance**: Gate thresholds ($\text{coverage\_tolerance} = 0.07$, $\text{min\_skill} = 0.0$) remain unadjusted.

### 4. Diagnostic of Synthetic Onion & Tomato Failure
- **Root Cause**: The synthetic generator (`generate_all_synthetic_data.py`) modeled severe seasonal sinusoidal swings ($\pm 50\%$ amplitude for Tomato, peak in July; $\pm 35\%$ for Onion).
- **Out-of-Distribution Shift**: In the training window (Aug 2024 – Apr 2025), Tomato prices averaged ₹1,170 (max target ₹1,997). In the test window (Jul – Aug 2025), prices reached ₹2,107–₹2,376.
- **Tree Regressor Extrapolation Boundary**: LightGBM cannot predict higher than the maximum target in its training leaves ($\sim$₹1,850).
- **Persistence Superiority**: Persistence ($B_0$) carried the prevailing ₹2,100 price forward, easily outperforming LightGBM's bounded under-predictions. Hence, synthetic models exhibited negative skill ($-65\%$ to $-503\%$) and rightly failed the usability gate.
- **Calibration Code Path**: CQR intervals are now fully integrated into the gating evaluator (`conformal_lower_80`, `conformal_upper_80`).

### 5. Baseline B3 & Confidence Intervals
- Baseline $B_3$ (Empirical Return Distribution per PRD §6.4) is computed from trailing-window $h$-day log return quantiles: $\hat{y}_{t+h}^{(q)} = P_t \cdot \exp(\hat{r}_q)$.
- 95% bootstrap confidence intervals are computed for both $\text{Skill vs } B_0$ and $\text{Skill vs } B_3$ and reported across all horizons.

## ADR-003: Model Configuration Alignment, Log-Return Targets, Block Bootstrap, and Walk-Forward Evaluation

### Status
Accepted (Production Serving Alignment)

### 1. Model Configuration for Forecast Usability Gates (`forecast_gates.json`)
- **Previous State**: Gating metrics in `forecast_gates.json` were previously computed from a static CQR fit on 70% train and evaluated on 15% validation.
- **Serving Configuration Alignment (PRD §6.5)**: The gate must reflect the identical model configuration served in production. Per PRD §6.5, this is **rolling refit every 14 days with trailing 45-day calibration**.
- **Implementation**: In Stage 5 of `sell_smart/scripts/run_pipeline.py`, the validation window ($T_{\text{val}} = \text{2025-04-27}$ to $\text{2025-06-21}$) is stepped every 14 days. For each refit date $r$, historical training data is purged of lookahead leakage ($t + h \le r - 1\text{d}$), split into $T_{\text{train\_fit}} \le r - 45\text{d}$ and trailing calibration $T_{\text{calib}} \in (r - 45\text{d}, r]$, and CQR margins are calibrated on nested pairs. Predictions on the subsequent 14-day serving chunk are concatenated across the validation period.
- **Two-Sided Coverage Band & Over-Coverage**:
  - The PRD §6.8 gating condition is two-sided: $|\text{Coverage}_{80} - 80\%| \le 7\%$, defining the acceptable band as $[73\%, 87\%]$.
  - **Treatment of Over-Coverage**: A two-sided band intentionally treats **over-coverage (> 87%) as a FAIL**. While a one-sided safety check only penalizes under-coverage, in agricultural marketing over-coverage signifies that prediction intervals are excessively conservative and uninformatively wide. Wide intervals (e.g. ₹2,000–₹5,000) inflate downside risk penalties in risk-adjusted net return calculations, paralyzing the decision engine and preventing actionable hold/switch advice.
  - **Results on Validation Under Rolling Refit**:
    - **Soybean**: $h \in \{1\text{d}, 3\text{d}, 7\text{d}, 10\text{d}\}$ PASS (80.7%–84.7% coverage, skill $+29.0\%$ to $+34.4\%$). Horizons $14\text{d}$ (88.9%) and $21\text{d}$ (88.3%) FAIL strictly due to over-coverage ($> 87\%$).
    - **Onion**: $h \in \{1\text{d}, 3\text{d}, 7\text{d}, 21\text{d}\}$ PASS (82.5%–86.9% coverage, skill $+36.2\%$ to $+56.8\%$). Horizons $10\text{d}$ (90.1%) and $14\text{d}$ (89.0%) FAIL due to over-coverage ($> 87\%$).
    - **Tomato**: $h \in \{1\text{d}, 3\text{d}, 7\text{d}, 10\text{d}, 14\text{d}\}$ PASS (80.0%–85.0% coverage, skill $+35.6\%$ to $+50.0\%$). Horizon $21\text{d}$ (91.4%) FAILS due to over-coverage ($> 87\%$).

### 2. LightGBM Target: Price Levels vs Log-Returns (PRD §6.2)
- **Diagnosis**: LightGBM was previously fitted on raw nominal price levels ($P_{t+h}$). Decision trees cannot extrapolate beyond the maximum target observed in their leaf nodes during training. When out-of-sample prices rose (e.g., Tomato prices surging to ₹2,376 in summer 2025 vs ₹1,850 maximum in training), the model severely under-predicted, resulting in massive negative skill against persistence ($-65\%$ to $-503\%$).
- **Switch to Log-Return Target**: In `sell_smart/src/sellsmart/forecast/lgbm_quantile.py`, the target was switched to relative log-returns per PRD §6.2:
  $$y = \ln\left(\frac{P[mandi, t+h]}{P_{\text{ref}}}\right), \quad P_{\text{ref}} = P_{\text{modal}}(t)$$
  and converted back to ₹/quintal via $P_q = P_{\text{ref}} \cdot \exp(y_q)$.
- **Re-evaluation on Validation**: Eliminates level drift entirely, restoring strong positive skill over naive persistence ($B_0$) across all crops (+29% to +57%).

### 3. Weekly Block Bootstrap
- **Replacement**: Replaced independent random sample bootstrapping with **calendar week block bootstrap** (`dates.dt.to_period('W')`).
- **Rationale**: Consecutive trading days within a week exhibit strong autoregressive error correlations, and co-located mandis within the same trading week experience contemporaneous weather/supply shocks. Resampling entire week blocks preserves both temporal autocorrelation and cross-mandi spatial covariance, providing honest 95% confidence intervals for skill metrics.

### 4. Walk-Forward Coverage & Skill Table (Full Window including July–August)
**Label: test period previously viewed (ADR-002)**  
Full evaluation window: 2025-04-27 to 2025-08-14 (spanning both validation and previously viewed test period with rolling refit every 14 days and trailing 45-day calibration). Comparison between Standard CQR and Online Adaptive Conformal Inference (ACI, $\gamma = 0.02, \alpha = 0.20$):

| Crop | Horizon | Samples | M1 Loss (₹/q) | B0 Loss (₹/q) | Skill vs B0 | Skill vs B3 | Standard P80 Cov [95% CI] | ACI P80 Cov [95% CI] |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Soybean** | 1d | 1,633 | ₹37.3 | ₹52.4 | +28.8% | +0.1% | 79.1% [77.1%, 81.0%] | 78.9% [76.8%, 80.8%] |
| **Soybean** | 3d | 1,603 | ₹47.9 | ₹73.9 | +35.3% | -0.8% | 79.4% [77.4%, 81.3%] | 78.7% [76.7%, 80.7%] |
| **Soybean** | 7d | 1,543 | ₹51.6 | ₹79.6 | +35.3% | -2.2% | 78.2% [76.0%, 80.2%] | 77.5% [75.3%, 79.5%] |
| **Soybean** | 10d | 1,499 | ₹55.9 | ₹84.8 | +34.1% | -4.5% | 76.0% [73.8%, 78.1%] | 75.7% [73.4%, 77.8%] |
| **Soybean** | 14d | 1,439 | ₹55.7 | ₹89.4 | +37.8% | +0.2% | 79.9% [77.7%, 81.8%] | 77.1% [74.9%, 79.2%] |
| **Soybean** | 21d | 1,334 | ₹60.6 | ₹97.8 | +38.0% | -0.4% | 78.3% [76.0%, 80.4%] | 75.9% [73.5%, 78.1%] |
| **Onion** | 1d | 545 | ₹14.5 | ₹22.7 | +36.5% | +4.4% | 85.1% [81.9%, 87.9%] | 81.3% [77.8%, 84.3%] |
| **Onion** | 3d | 535 | ₹23.5 | ₹40.7 | +42.2% | +6.7% | 86.5% [83.4%, 89.2%] | 83.2% [79.8%, 86.1%] |
| **Onion** | 7d | 515 | ₹33.1 | ₹56.5 | +41.4% | +7.5% | 83.5% [80.0%, 86.5%] | 82.1% [78.6%, 85.2%] |
| **Onion** | 10d | 500 | ₹38.9 | ₹67.1 | +42.0% | +8.4% | 84.6% [81.2%, 87.5%] | 81.4% [77.8%, 84.6%] |
| **Onion** | 14d | 480 | ₹42.9 | ₹78.5 | +45.4% | +13.0% | 85.6% [82.2%, 88.5%] | 82.7% [79.1%, 85.8%] |
| **Onion** | 21d | 445 | ₹46.0 | ₹92.8 | +50.4% | +23.7% | 80.7% [76.8%, 84.1%] | 79.1% [75.1%, 82.6%] |
| **Tomato** | 1d | 436 | ₹11.2 | ₹17.5 | +36.1% | +9.6% | 81.4% [77.5%, 84.8%] | 79.6% [75.6%, 83.1%] |
| **Tomato** | 3d | 428 | ₹19.4 | ₹31.6 | +38.6% | +10.8% | 82.2% [78.3%, 85.6%] | 79.9% [75.9%, 83.4%] |
| **Tomato** | 7d | 412 | ₹29.6 | ₹46.9 | +37.0% | +13.0% | 79.9% [75.7%, 83.4%] | 79.1% [74.9%, 82.8%] |
| **Tomato** | 10d | 400 | ₹34.9 | ₹53.2 | +34.4% | +12.1% | 80.5% [76.3%, 84.1%] | 78.0% [73.7%, 81.8%] |
| **Tomato** | 14d | 384 | ₹41.5 | ₹64.5 | +35.6% | +14.2% | 74.2% [69.6%, 78.3%] | 74.7% [70.2%, 78.8%] |
| **Tomato** | 21d | 356 | ₹52.8 | ₹84.5 | +37.5% | +17.8% | 73.6% [68.8%, 77.9%] | 73.0% [68.2%, 77.4%] |

### 5. Invariance of Gate Thresholds
- All gate parameters remain strictly invariant: `coverage_tolerance = 0.07`, `min_skill = 0.0`.
- All unit and golden tests pass (72/72 green). No LLM pipeline code was modified or invoked.

