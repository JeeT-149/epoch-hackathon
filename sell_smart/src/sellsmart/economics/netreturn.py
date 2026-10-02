"""
sell_smart.economics.netreturn
Net return computation: price - spoilage_loss - transport - storage - fees.
All money in ₹ per original quintal harvested (R8).
"""
from __future__ import annotations

from sellsmart.economics.spoilage import compute_spoilage_fraction
from sellsmart.economics.transport import compute_transport_cost
from sellsmart.economics.storage import compute_storage_cost
from sellsmart.economics.fees import compute_fees
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def compute_net_return(
    crop: str,
    modal_price: float,
    days_held: int,
    distance_km: float,
    quantity_q: float,
    crops_config: dict,
    storage_condition: str = "ambient",
    quality_factor: float = 1.0,
    road_factor: float = 1.35,
    village_lat: float | None = None,
    village_lon: float | None = None,
    mandi_lat: float | None = None,
    mandi_lon: float | None = None,
) -> dict:
    """
    Compute net return per original quintal harvested.

    Net return = (modal_price × (1 - spoilage_fraction)) - transport - storage - fees

    Returns a dict with full breakdown and is_placeholder flag.
    """
    # Spoilage
    spoilage_frac = compute_spoilage_fraction(
        crop, days_held, storage_condition, quality_factor, crops_config
    )
    effective_quantity = quantity_q * (1 - spoilage_frac)
    # Price received is on effective quantity, but we report per ORIGINAL quintal
    gross_revenue_per_orig_q = modal_price * (1 - spoilage_frac)

    # Transport
    transport = compute_transport_cost(
        distance_km=distance_km,
        quantity_q=effective_quantity,
        crop=crop,
        crops_config=crops_config,
        road_factor=road_factor,
        village_lat=village_lat,
        village_lon=village_lon,
        mandi_lat=mandi_lat,
        mandi_lon=mandi_lon,
    )

    # Storage
    storage = compute_storage_cost(crop, days_held, quantity_q, crops_config)

    # Fees (on effective price × quantity)
    fees = compute_fees(crop, modal_price, effective_quantity, crops_config)

    # Net return per original quintal
    net_return = (
        gross_revenue_per_orig_q
        - transport["cost_per_q"] * (effective_quantity / max(quantity_q, 1))
        - storage["cost_per_q"]
        - fees["total_fees_per_q"] * (1 - spoilage_frac)
    )

    is_placeholder = (
        transport["is_placeholder"]
        or storage["is_placeholder"]
        or fees["is_placeholder"]
    )

    return {
        "net_return_per_q": round(net_return, 2),
        "gross_revenue_per_q": round(gross_revenue_per_orig_q, 2),
        "modal_price": modal_price,
        "spoilage_fraction": round(spoilage_frac, 4),
        "transport_cost_per_q": transport["cost_per_q"],
        "storage_cost_per_q": storage["cost_per_q"],
        "fees_per_q": fees["total_fees_per_q"],
        "days_held": days_held,
        "distance_km": distance_km,
        "road_km": transport["road_km"],
        "vehicle": transport["vehicle"],
        "is_placeholder": is_placeholder,
        "modal_price_proxy_note": (
            "Modal price is a market-level reference, not a guaranteed realisation price (R9)."
        ),
    }
