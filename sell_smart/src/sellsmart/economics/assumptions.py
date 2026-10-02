"""
sell_smart.economics.assumptions
Generates and validates the Assumptions Register (docs/assumptions_register.md).
Strictly implements Rule R6 and PRD Section 7 & Appendix D.3.
Ensures demo_ready=False whenever any parameter has source == "PLACEHOLDER".
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

from sellsmart.common.config import load_crops_config
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def build_assumptions_register(
    crops_config: dict | None = None,
    output_path: Path | str | None = None,
) -> tuple[pd.DataFrame, bool]:
    """
    Builds the assumptions register table and evaluates demo_ready status.

    Returns:
        (register_df: pd.DataFrame, demo_ready: bool)
    """
    if crops_config is None:
        crops_config = load_crops_config()

    rows: List[Dict[str, Any]] = []

    for crop, cfg in crops_config.items():
        crop_name = cfg.get("display_name", crop.capitalize())

        # Spoilage
        spoilage = cfg.get("spoilage", {})
        sp_src = spoilage.get("source", "PLACEHOLDER")
        rows.append({
            "Parameter": f"{crop_name} Spoilage Base Rate",
            "Value": spoilage.get("daily_rate_pct", "N/A"),
            "Unit": "% weight loss / day",
            "Source Status": sp_src,
            "Used In": "compute_spoilage_fraction",
            "Sensitivity": "High (shifts holding horizon)",
            "Owner to Verify": "ICAR / Field agronomist",
        })

        # Storage
        storage = cfg.get("storage", {})
        st_src = storage.get("source", "PLACEHOLDER")
        rows.append({
            "Parameter": f"{crop_name} Storage Cost",
            "Value": storage.get("cost_per_q_per_day", "N/A"),
            "Unit": "₹/quintal/day",
            "Source Status": st_src,
            "Used In": "compute_storage_cost",
            "Sensitivity": "Medium (linear cost erosion)",
            "Owner to Verify": "Mandi / FPO survey",
        })

        # Transport
        transport = cfg.get("transport", {})
        loading_src = transport.get("loading_source", "PLACEHOLDER")
        rows.append({
            "Parameter": f"{crop_name} Loading & Handling Cost",
            "Value": transport.get("loading_cost_per_q", "N/A"),
            "Unit": "₹/quintal",
            "Source Status": loading_src,
            "Used In": "compute_transport_cost",
            "Sensitivity": "Low (fixed terminal cost)",
            "Owner to Verify": "Transporter field survey",
        })

        for v in transport.get("vehicle_types", []):
            v_src = v.get("source", "PLACEHOLDER")
            rows.append({
                "Parameter": f"{crop_name} Transport Rate ({v.get('name')})",
                "Value": v.get("cost_per_km", "N/A"),
                "Unit": "₹/km (trip-based)",
                "Source Status": v_src,
                "Used In": "compute_transport_cost",
                "Sensitivity": "High (scales with distance)",
                "Owner to Verify": "RTO / Transport union rates",
            })

        # Fees
        fees = cfg.get("fees", {})
        fee_src = fees.get("source", "PLACEHOLDER")
        rows.append({
            "Parameter": f"{crop_name} Farmer Mandi Commission",
            "Value": f"{fees.get('mandi_commission_pct', 0.0)}%",
            "Unit": "% of gross revenue",
            "Source Status": fee_src,
            "Used In": "compute_fees",
            "Sensitivity": "High (statutory deduction)",
            "Owner to Verify": "State APMC Act (Verified)",
        })
        rows.append({
            "Parameter": f"{crop_name} Weighing & Hamali Charge",
            "Value": fees.get("weighing_per_q", "N/A"),
            "Unit": "₹/quintal",
            "Source Status": fee_src,
            "Used In": "compute_fees",
            "Sensitivity": "Low (statutory flat fee)",
            "Owner to Verify": "APMC Gazette Notification",
        })

        # MSP if present
        if "msp" in cfg:
            msp = cfg.get("msp", {})
            rows.append({
                "Parameter": f"{crop_name} Minimum Support Price (MSP)",
                "Value": msp.get("value_rs_per_q", "N/A"),
                "Unit": "₹/quintal",
                "Source Status": msp.get("source", "PLACEHOLDER"),
                "Used In": "baseline comparison",
                "Sensitivity": "Medium (price floor reference)",
                "Owner to Verify": "CCEA Kharif/Rabi Notification",
            })

    df = pd.DataFrame(rows)

    # Rule R6: demo_ready=False if any PLACEHOLDER remains
    has_placeholder = (df["Source Status"] == "PLACEHOLDER").any()
    demo_ready = not has_placeholder

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        table_md = df.to_markdown(index=False)
        content = f"""# Assumptions & Parameter Provenance Register (PRD Rule R6 & Appendix D.3)

- **Registry Status**: `{'DEMO READY' if demo_ready else 'DEMO NOT READY (PLACEHOLDER PARAMETERS DETECTED)'}`
- **demo_ready**: `{str(demo_ready).lower()}`
- **Rule Enforcement**: Any economic parameter whose source status is `PLACEHOLDER` programmatically forces `demo_ready=false` and displays prominent farmer-facing disclaimers.

## Parameter Provenance Table

{table_md}
"""
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Assumptions register written to {out_p}. demo_ready={demo_ready}")

    return df, demo_ready
