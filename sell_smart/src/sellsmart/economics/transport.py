"""
sell_smart.economics.transport
Transport cost computation from village to mandi.
All costs are PLACEHOLDER (R6) until verified.
Units: ₹ per original quintal harvested (R8).
"""
from __future__ import annotations

import math

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def compute_transport_cost(
    distance_km: float,
    quantity_q: float,
    crop: str,
    crops_config: dict,
    road_factor: float = 1.35,
    village_lat: float | None = None,
    village_lon: float | None = None,
    mandi_lat: float | None = None,
    mandi_lon: float | None = None,
) -> dict:
    """
    Compute transport cost per original quintal harvested.

    If lat/lon provided, compute haversine distance x road_factor.
    Otherwise use provided distance_km directly.

    Returns dict with:
        cost_per_q: ₹/quintal
        road_km: actual road distance estimate
        vehicle: vehicle type used
        n_trips: number of trips
        source_note: PLACEHOLDER warning if applicable
    """
    if village_lat and mandi_lat:
        air_km = _haversine_km(village_lat, village_lon, mandi_lat, mandi_lon)
        road_km = air_km * road_factor
    else:
        road_km = distance_km * road_factor if distance_km else 0.0

    cfg = crops_config.get(crop, {}).get("transport", {})
    vehicles = cfg.get("vehicle_types", [])
    loading_cost_per_q = cfg.get("loading_cost_per_q", 15.0)
    source_note = "PLACEHOLDER"

    if not vehicles:
        logger.warning(f"No vehicle types configured for {crop}. Using fallback ₹25/km.")
        vehicles = [{"name": "truck", "capacity_q": 100, "cost_per_km": 25.0, "source": "PLACEHOLDER"}]

    # Select smallest vehicle with capacity >= quantity
    selected_vehicle = None
    n_trips = 1
    for v in sorted(vehicles, key=lambda x: x.get("capacity_q", 999)):
        if v.get("capacity_q", 0) >= quantity_q:
            selected_vehicle = v
            break
    if selected_vehicle is None:
        selected_vehicle = max(vehicles, key=lambda x: x.get("capacity_q", 0))
        cap = selected_vehicle.get("capacity_q", 1)
        n_trips = math.ceil(quantity_q / cap)

    cost_per_km = selected_vehicle.get("cost_per_km", 25.0)
    source_note = selected_vehicle.get("source", "PLACEHOLDER")
    vehicle_cost = cost_per_km * road_km * n_trips
    total_cost = vehicle_cost + (loading_cost_per_q * quantity_q)
    cost_per_q = total_cost / max(quantity_q, 1)

    return {
        "cost_per_q": round(cost_per_q, 2),
        "road_km": round(road_km, 2),
        "vehicle": selected_vehicle.get("name", "unknown"),
        "n_trips": n_trips,
        "loading_cost_per_q": loading_cost_per_q,
        "source_note": source_note,
        "is_placeholder": source_note == "PLACEHOLDER",
    }
