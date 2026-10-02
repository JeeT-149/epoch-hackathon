"""
sell_smart.calibration.plots
Calibration plots: reliability diagram, interval width distributions.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def plot_reliability_diagram(
    passport: dict,
    output_dir: Path,
    name: str = "reliability_diagram",
) -> Path:
    """
    Plot empirical vs target quantile coverage (reliability diagram).
    Saves to PNG.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return Path(output_dir) / f"{name}.png"

    calibration = passport.get("calibration", {})
    targets, empiricals = [], []
    for k, v in calibration.items():
        if k.startswith("q") and "target_coverage" in v:
            targets.append(v["target_coverage"])
            empiricals.append(v["empirical_fraction_below"])

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", label="Perfect calibration")
    ax.scatter(targets, empiricals, color="steelblue", s=80, zorder=5, label="Model")
    for t, e in zip(targets, empiricals):
        ax.annotate(f"q{int(t*100)}", (t, e), textcoords="offset points", xytext=(5, 0))

    ax.set_xlabel("Target quantile")
    ax.set_ylabel("Empirical fraction below")
    ax.set_title(f"Reliability Diagram — {passport.get('crop', '')} h={passport.get('horizon_days', '')}d")
    ax.legend()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.png"
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return path
