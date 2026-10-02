"""
sell_smart.decision.confidence
Confidence labelling: HIGH / MEDIUM / LOW based on DQ, model and economics scores.
"""
from __future__ import annotations


def compute_confidence(
    dq_score: float,
    model_interval_width: float,
    modal_price: float,
    is_placeholder: bool,
    config: dict,
    climate_summary: dict | None = None,
) -> tuple[str, float]:
    """
    Compute a composite confidence score and label.
    Optionally adjusts economics confidence using climate risk summary (disease and water stress).

    Returns: (label: 'HIGH'|'MEDIUM'|'LOW', score: float in [0,1])
    """
    cfg = config.get("confidence", {})
    dq_w = cfg.get("dq_weight", 0.4)
    model_w = cfg.get("model_weight", 0.3)
    econ_w = cfg.get("economics_weight", 0.3)
    thresholds = cfg.get("thresholds", {"HIGH": 0.70, "MEDIUM": 0.45})

    # Model confidence: inverse relative interval width
    rel_width = min(model_interval_width / max(modal_price, 1.0), 1.0)
    model_score = max(0.0, 1.0 - rel_width)

    # Economics confidence: 0 if placeholder, else 1.0 adjusted by climate risks
    econ_score = 0.0 if is_placeholder else 1.0
    if not is_placeholder and climate_summary:
        # High disease incidence and low water availability reduce confidence in net returns
        disease_rate = float(climate_summary.get("high_disease_rate", 0.0))
        water_stress_rate = float(climate_summary.get("low_water_rate", 0.0))
        risk_discount = 0.10 * disease_rate + 0.10 * water_stress_rate
        econ_score = max(0.0, econ_score * (1.0 - risk_discount))

    score = dq_w * dq_score + model_w * model_score + econ_w * econ_score

    if score >= thresholds.get("HIGH", 0.70):
        label = "HIGH"
    elif score >= thresholds.get("MEDIUM", 0.45):
        label = "MEDIUM"
    else:
        label = "LOW"

    return label, round(score, 4)
