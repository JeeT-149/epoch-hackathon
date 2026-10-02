"""
sell_smart.forecast.gating
Model Gating and Skill Evaluation (PRD Section 6.4, 6.8 & Section 14).

Computes:
  - Pinball (quantile) loss per quantile and mean pinball loss.
  - Skill score vs Persistence (B0) and Rolling Mean (B2).
  - Empirical coverage at nominal 50%, 80%, 90% with Wilson 95% confidence intervals.
  - Gating decision (`forecast_usable`):
      Pass rule: |coverage_80 - 0.80| <= tolerance (default 0.07) AND skill_B0 > 0.
      If a model fails gating, forecast_usable = False, and the decision engine
      restricts recommendations to "where" (spatial comparison at h=0), disabling "when" (hold).
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, q: float) -> float:
    """
    Compute pinball loss for quantile q.
    L_q(y, y_hat) = max(q * (y - y_hat), (q - 1) * (y - y_hat))
    """
    diff = y_true - y_pred
    loss = np.maximum(q * diff, (q - 1.0) * diff)
    return float(np.mean(loss))


def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    """Compute Wilson score interval for binomial proportion."""
    if total == 0:
        return 0.0, 1.0
    z = 1.95996  # 95% confidence
    p = successes / total
    denom = 1.0 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    spread = z * np.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denom
    return float(max(0.0, centre - spread)), float(min(1.0, centre + spread))


def winkler_interval_score(y_true: np.ndarray, lower: np.ndarray, upper: np.ndarray, alpha: float = 0.20) -> float:
    """
    Winkler Interval Score for nominal (1 - alpha) interval (PRD Section 6.4).
    IS_alpha = (U - L) + (2/alpha)*(L - y)*I(y < L) + (2/alpha)*(y - U)*I(y > U)
    """
    width = upper - lower
    penalty_low = np.maximum(0.0, lower - y_true) * (2.0 / alpha)
    penalty_high = np.maximum(0.0, y_true - upper) * (2.0 / alpha)
    return float(np.mean(width + penalty_low + penalty_high))


def bootstrap_skill_ci(
    y_true: np.ndarray,
    m1_preds: dict[float, np.ndarray],
    base_preds: dict[float, np.ndarray],
    quantiles: list[float],
    dates: np.ndarray | None = None,
    n_boot: int = 500,
    seed: int = 42,
) -> tuple[float, float]:
    """
    Calculate 95% block bootstrap confidence interval for skill score = 1 - Loss(M1)/Loss(Base).
    Resamples blocks by week when dates are provided to respect temporal and spatial autocorrelation.
    """
    n = len(y_true)
    if n < 10:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    m1_loss_per_sample = np.zeros(n)
    base_loss_per_sample = np.zeros(n)
    for q in quantiles:
        if q in m1_preds and q in base_preds:
            diff_m = y_true - m1_preds[q]
            m1_loss_per_sample += np.maximum(q * diff_m, (q - 1.0) * diff_m) / len(quantiles)
            diff_b = y_true - base_preds[q]
            base_loss_per_sample += np.maximum(q * diff_b, (q - 1.0) * diff_b) / len(quantiles)

    skills = []
    if dates is not None and len(dates) == n:
        # Group observations by calendar week
        weeks = pd.to_datetime(dates).to_period("W").astype(str).values
        unique_weeks, inverse = np.unique(weeks, return_inverse=True)
        week_indices = [np.where(inverse == i)[0] for i in range(len(unique_weeks))]
        n_blocks = len(unique_weeks)
        for _ in range(n_boot):
            sampled_week_indices = rng.choice(n_blocks, size=n_blocks, replace=True)
            sampled_idx = np.concatenate([week_indices[w] for w in sampled_week_indices])
            m_mean = float(np.mean(m1_loss_per_sample[sampled_idx]))
            b_mean = float(np.mean(base_loss_per_sample[sampled_idx]))
            if b_mean > 0:
                skills.append(1.0 - (m_mean / b_mean))
    else:
        # Contiguous 7-day block bootstrap fallback
        block_size = min(7, max(2, n // 2))
        n_blocks = max(1, n // block_size)
        for _ in range(n_boot):
            start_indices = rng.choice(max(1, n - block_size + 1), size=n_blocks, replace=True)
            sampled_idx = np.concatenate([np.arange(s, min(s + block_size, n)) for s in start_indices])
            m_mean = float(np.mean(m1_loss_per_sample[sampled_idx]))
            b_mean = float(np.mean(base_loss_per_sample[sampled_idx]))
            if b_mean > 0:
                skills.append(1.0 - (m_mean / b_mean))

    if not skills:
        return (0.0, 0.0)
    return float(np.percentile(skills, 2.5)), float(np.percentile(skills, 97.5))


def evaluate_forecast_gate(
    y_true: np.ndarray,
    m1_quantile_preds: dict[float, np.ndarray],
    b0_quantile_preds: dict[float, np.ndarray],
    b2_quantile_preds: dict[float, np.ndarray] | None = None,
    b3_quantile_preds: dict[float, np.ndarray] | None = None,
    crop: str = "",
    horizon: int = 1,
    coverage_tolerance: float = 0.07,
    conformal_lower_80: np.ndarray | None = None,
    conformal_upper_80: np.ndarray | None = None,
    conformal_lower_90: np.ndarray | None = None,
    conformal_upper_90: np.ndarray | None = None,
    dates: np.ndarray | None = None,
) -> dict:
    """
    Evaluate pinball loss, baseline skill scores vs B0, B2, B3 (with 95% block bootstrap CIs),
    conformal coverage, interval score, and forecast usability gate.
    """
    n = len(y_true)
    if n == 0:
        return {
            "crop": crop,
            "horizon_days": horizon,
            "forecast_usable": False,
            "gate_reason": "no_test_samples",
            "skill_vs_b0": 0.0,
            "pinball_loss_m1": np.nan,
        }

    quantiles = sorted(m1_quantile_preds.keys())

    # 1. Pinball loss per quantile and mean across quantiles
    loss_m1_per_q = {}
    loss_b0_per_q = {}
    loss_b2_per_q = {}
    loss_b3_per_q = {}

    for q in quantiles:
        loss_m1_per_q[q] = pinball_loss(y_true, m1_quantile_preds[q], q)
        if q in b0_quantile_preds:
            loss_b0_per_q[q] = pinball_loss(y_true, b0_quantile_preds[q], q)
        if b2_quantile_preds and q in b2_quantile_preds:
            loss_b2_per_q[q] = pinball_loss(y_true, b2_quantile_preds[q], q)
        if b3_quantile_preds and q in b3_quantile_preds:
            loss_b3_per_q[q] = pinball_loss(y_true, b3_quantile_preds[q], q)

    mean_loss_m1 = float(np.mean(list(loss_m1_per_q.values())))
    mean_loss_b0 = float(np.mean(list(loss_b0_per_q.values()))) if loss_b0_per_q else np.nan
    mean_loss_b2 = float(np.mean(list(loss_b2_per_q.values()))) if loss_b2_per_q else np.nan
    mean_loss_b3 = float(np.mean(list(loss_b3_per_q.values()))) if loss_b3_per_q else np.nan

    # 2. Skill scores vs baselines: 1 - Loss(M1) / Loss(Base)
    skill_vs_b0 = float(1.0 - (mean_loss_m1 / mean_loss_b0)) if mean_loss_b0 > 0 else 0.0
    skill_vs_b2 = float(1.0 - (mean_loss_m1 / mean_loss_b2)) if mean_loss_b2 > 0 else 0.0
    skill_vs_b3 = float(1.0 - (mean_loss_m1 / mean_loss_b3)) if not np.isnan(mean_loss_b3) and mean_loss_b3 > 0 else "n/a"

    # Bootstrap CIs for Skill vs B0 and B3 (weekly block bootstrap)
    skill_vs_b0_ci = bootstrap_skill_ci(y_true, m1_quantile_preds, b0_quantile_preds, quantiles, dates=dates)
    skill_vs_b3_ci = None
    if b3_quantile_preds and not np.isnan(mean_loss_b3):
        skill_vs_b3_ci = bootstrap_skill_ci(y_true, m1_quantile_preds, b3_quantile_preds, quantiles, dates=dates)

    # 3. Empirical coverage at nominal 80% (q10 to q90) and 90% (q05 to q95)
    # Use conformal bounds if supplied; else raw quantile predictions
    lo_80 = conformal_lower_80 if conformal_lower_80 is not None else m1_quantile_preds.get(0.10)
    hi_80 = conformal_upper_80 if conformal_upper_80 is not None else m1_quantile_preds.get(0.90)

    cov_80 = np.nan
    cov_80_ci = (0.0, 1.0)
    interval_score_80 = np.nan
    if lo_80 is not None and hi_80 is not None:
        covered = (y_true >= lo_80) & (y_true <= hi_80)
        cov_80 = float(covered.mean())
        cov_80_ci = wilson_interval(int(covered.sum()), n)
        interval_score_80 = winkler_interval_score(y_true, lo_80, hi_80, alpha=0.20)

    lo_90 = conformal_lower_90 if conformal_lower_90 is not None else m1_quantile_preds.get(0.05)
    hi_90 = conformal_upper_90 if conformal_upper_90 is not None else m1_quantile_preds.get(0.95)

    cov_90 = np.nan
    cov_90_ci = (0.0, 1.0)
    interval_score_90 = np.nan
    if lo_90 is not None and hi_90 is not None:
        covered = (y_true >= lo_90) & (y_true <= hi_90)
        cov_90 = float(covered.mean())
        cov_90_ci = wilson_interval(int(covered.sum()), n)
        interval_score_90 = winkler_interval_score(y_true, lo_90, hi_90, alpha=0.10)

    # 4. Gate decision (PRD 6.8 & 14)
    # Pass rule: |cov_80 - 0.80| <= coverage_tolerance AND skill_vs_b0 >= 0
    coverage_ok = (not np.isnan(cov_80)) and (abs(cov_80 - 0.80) <= coverage_tolerance)
    skill_ok = skill_vs_b0 >= 0.0
    forecast_usable = coverage_ok and skill_ok

    reason = "PASSED: Calibrated coverage and positive skill over baselines."
    if not coverage_ok and not skill_ok:
        reason = f"FAILED: Uncalibrated coverage ({cov_80:.1%} vs 80%) and negative skill ({skill_vs_b0:+.1%})."
    elif not coverage_ok:
        reason = f"FAILED: P80 coverage ({cov_80:.1%}) outside tolerance +/-{coverage_tolerance:.0%}."
    elif not skill_ok:
        reason = f"FAILED: Model failed to beat persistence baseline B0 (skill={skill_vs_b0:+.1%})."

    gate_result = {
        "crop": crop,
        "horizon_days": horizon,
        "n_samples": n,
        "forecast_usable": bool(forecast_usable),
        "gate_reason": reason,
        "mean_pinball_loss_m1": round(mean_loss_m1, 2),
        "mean_pinball_loss_b0": round(mean_loss_b0, 2) if not np.isnan(mean_loss_b0) else None,
        "mean_pinball_loss_b2": round(mean_loss_b2, 2) if not np.isnan(mean_loss_b2) else None,
        "mean_pinball_loss_b3": round(mean_loss_b3, 2) if not np.isnan(mean_loss_b3) else None,
        "skill_vs_b0": round(skill_vs_b0, 4),
        "skill_vs_b0_ci": [round(skill_vs_b0_ci[0], 4), round(skill_vs_b0_ci[1], 4)] if skill_vs_b0_ci else None,
        "skill_vs_b2": round(skill_vs_b2, 4),
        "skill_vs_b3": skill_vs_b3 if isinstance(skill_vs_b3, str) else round(skill_vs_b3, 4),
        "skill_vs_b3_ci": [round(skill_vs_b3_ci[0], 4), round(skill_vs_b3_ci[1], 4)] if skill_vs_b3_ci else None,
        "interval_score_80": round(interval_score_80, 2) if not np.isnan(interval_score_80) else None,
        "interval_score_90": round(interval_score_90, 2) if not np.isnan(interval_score_90) else None,
        "empirical_coverage_80": round(cov_80, 4) if not np.isnan(cov_80) else None,
        "coverage_80_wilson_ci": [round(cov_80_ci[0], 4), round(cov_80_ci[1], 4)],
        "empirical_coverage_90": round(cov_90, 4) if not np.isnan(cov_90) else None,
    }
    return gate_result


def save_forecast_gates(gates: list[dict], output_path: Path | str) -> None:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(gates, f, indent=2)
    logger.info(f"Forecast gates written to {p}")


def save_metrics_markdown_table(gates: list[dict], output_path: Path | str) -> Path:
    """
    Format a comprehensive markdown table of forecast metrics for each crop and horizon.
    Includes Pinball Loss, Interval Score, Coverage, and Skill vs B0, B2, B3 with 95% CIs.
    """
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "Crop", "Horizon", "M1 Pinball", "P80 Interval Score",
        "P80 Coverage (Wilson 95% CI)", "P90 Coverage",
        "Skill vs B0 (Persistence) [95% CI]", "Skill vs B2 (7d Roll)", "Skill vs B3 (Empirical Returns) [95% CI]",
        "Gate Status"
    ]
    rows = []
    for g in gates:
        cov_ci = g.get("coverage_80_wilson_ci", [0, 0])
        ci_str = f"[{cov_ci[0]:.1%}, {cov_ci[1]:.1%}]" if cov_ci else ""
        cov_str = f"{g['empirical_coverage_80']:.1%} {ci_str}" if g.get("empirical_coverage_80") is not None else "n/a"
        cov90_str = f"{g['empirical_coverage_90']:.1%}" if g.get("empirical_coverage_90") is not None else "n/a"

        # B0 skill with CI
        b0_val = g.get("skill_vs_b0")
        b0_ci = g.get("skill_vs_b0_ci")
        if isinstance(b0_val, (int, float)):
            b0_str = f"{b0_val:+.1%}"
            if b0_ci:
                b0_str += f" [{b0_ci[0]:+.1%}, {b0_ci[1]:+.1%}]"
        else:
            b0_str = str(b0_val)

        # B2 skill
        b2_val = g.get("skill_vs_b2")
        b2_str = f"{b2_val:+.1%}" if isinstance(b2_val, (int, float)) else str(b2_val)

        # B3 skill with CI
        b3_val = g.get("skill_vs_b3")
        b3_ci = g.get("skill_vs_b3_ci")
        if isinstance(b3_val, (int, float)):
            b3_str = f"{b3_val:+.1%}"
            if b3_ci:
                b3_str += f" [{b3_ci[0]:+.1%}, {b3_ci[1]:+.1%}]"
        else:
            b3_str = str(b3_val)

        status = "✅ PASS" if g.get("forecast_usable") else "❌ FAIL (Spatial only)"

        rows.append([
            g.get("crop", "").capitalize(),
            f"{g.get('horizon_days')}d",
            f"₹{g.get('mean_pinball_loss_m1', 0):.1f}/q",
            f"₹{g.get('interval_score_80', 0):.1f}/q" if g.get("interval_score_80") is not None else "n/a",
            cov_str,
            cov90_str,
            b0_str,
            b2_str,
            b3_str,
            status,
        ])

    df = pd.DataFrame(rows, columns=headers)
    table_md = df.to_markdown(index=False)

    content = f"""# Forecast Metrics & Benchmark Evaluation Table (PRD Sections 6.4, 6.8 & 14)

**Evaluation Protocol**:
- Split: Time-ordered 70% Train / 15% Validation (Calibration) / 15% Test.
- Embargo: 21 days between splits ($\\max(H) = 21$ days).
- Baselines:
  - $B_0$: Naive persistence ($y_{{t+h}} = y_t$) with empirical return quantiles
  - $B_2$: 7-day rolling mean
  - $B_3$: Empirical return distribution: trailing-window quantiles of $h$-day log returns per crop and mandi cluster
- Gating Rule (PRD §6.8): Forecast usable if $|\\text{{Coverage}}_{{80}} - 80\\%| \\le 7\\%$ on validation and $\\text{{Skill}}(M_1, B_0) \\ge 0$. If failed, holding advice is disabled and recommendations answer WHERE ($h=0$) only.

{table_md}
"""
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Forecast metrics table saved to {p}")
    return p

