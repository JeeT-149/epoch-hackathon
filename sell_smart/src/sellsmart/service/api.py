"""
sell_smart.service.api
Implements the /v1/advice endpoint logic per PRD Section 8.7 & 15.1.
Enforces ADR-001: Every response carries is_synthetic and price_source.
For synthetic crops (Onion & Tomato), visibly discloses simulated prices and disables headline ₹ claims.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd
import numpy as np

from sellsmart.common.config import load_config, load_crops_config, load_mandis_config
from sellsmart.decision.options import generate_options
from sellsmart.decision.engine import decide, DecisionResult
from sellsmart.economics.netreturn import compute_net_return
from sellsmart.decision.confidence import compute_confidence
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

ROOT = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = ROOT / "config"
GOLD_DIR = ROOT / "data" / "gold"
ARTIFACTS_DIR = ROOT / "artifacts"


class AdviceService:
    """
    Stateless decision service computing risk-aware selling advice.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = Path(config_dir) if config_dir else CONFIG_DIR
        self.config = load_config(config_dir=self.config_dir)
        self.crops_cfg = load_crops_config(config_dir=self.config_dir)
        self.mandis_cfg = load_mandis_config(config_dir=self.config_dir)

        # Load tuned decision parameters (PRD Step 4)
        params_file = ARTIFACTS_DIR / "decision_params.json"
        if not params_file.exists():
            params_file = self.config_dir / "decision_params.json"
        self.decision_params = {}
        if params_file.exists():
            try:
                import json
                with open(params_file, "r", encoding="utf-8") as f:
                    self.decision_params = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load decision params: {e}")

    def get_advice(
        self,
        crop: str,
        quantity_q: float = 20.0,
        village_text: str = "",
        village_lat: Optional[float] = None,
        village_lon: Optional[float] = None,
        cash_deadline_days: int = 7,
        trader_offer_per_q: Optional[float] = None,
        storage_available: bool = True,
        storage_condition: str = "ambient",
        quality_factor: float = 1.0,
        as_of: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Produce risk-aware selling advice for farmer input.
        """
        crop_clean = crop.lower().strip()
        # Normalise synonym
        if "soya" in crop_clean:
            crop_clean = "soybean"
        elif "kanda" in crop_clean or "pyaz" in crop_clean:
            crop_clean = "onion"
        elif "tamatar" in crop_clean:
            crop_clean = "tomato"

        today = date.today() if as_of is None else pd.to_datetime(as_of).date()
        v_lat = village_lat if village_lat is not None else 20.0
        v_lon = village_lon if village_lon is not None else 74.0

        # Filter mandis for crop
        all_mandis = self.mandis_cfg.get("mandis", [])
        crop_mandis = [m for m in all_mandis if m.get("crop") == crop_clean]
        if not crop_mandis:
            crop_mandis = [{"mandi_id": f"default_{crop_clean}_mandi", "lat": v_lat, "lon": v_lon, "market_raw": "Local Mandi"}]

        # Check forecast gates from artifacts if available
        gates_file = ARTIFACTS_DIR / "forecast_gates.json"
        forecast_usable = False
        if gates_file.exists():
            import json
            try:
                with open(gates_file) as f:
                    gates = json.load(f)
                h7_gate = next((g for g in gates if g.get("crop") == crop_clean and g.get("horizon_days") == 7), None)
                if h7_gate:
                    forecast_usable = bool(h7_gate.get("forecast_usable", False))
            except Exception as e:
                logger.warning(f"Could not read forecast gates: {e}")

        # Baseline modal price lookup from gold panel if available
        gold_path = GOLD_DIR / "gold_panel.parquet"
        baseline_price = 2200.0
        if gold_path.exists():
            try:
                df_gold = pd.read_parquet(gold_path)
                crop_gold = df_gold[df_gold["crop"] == crop_clean]["modal_price"].dropna()
                if len(crop_gold) > 0:
                    baseline_price = float(crop_gold.iloc[-1])
            except Exception:
                pass

        # Economics closure
        def _econ(m_info, days_held, modal_price=None):
            m_lat = m_info.get("lat") or v_lat
            m_lon = m_info.get("lon") or v_lon
            dist = max(5.0, np.sqrt(((v_lat - m_lat) * 111.0)**2 + ((v_lon - m_lon) * 111.0 * np.cos(np.radians(v_lat)))**2))
            mp = modal_price if (modal_price is not None and modal_price > 0) else baseline_price
            return compute_net_return(
                modal_price=mp,
                crop=crop_clean,
                distance_km=dist,
                quantity_q=quantity_q,
                days_held=days_held,
                crops_config=self.crops_cfg,
                storage_condition=storage_condition,
                quality_factor=quality_factor,
            )

        # Generate candidate options
        calendar_df = pd.DataFrame()
        options = generate_options(
            crop=crop_clean,
            today=today,
            mandis=crop_mandis,
            forecasts=pd.DataFrame(),
            calendar_df=calendar_df,
            economics_fn=_econ,
            max_days=14,
            cash_deadline_days=cash_deadline_days,
        )

        # Confidence calculation
        is_synth = crop_clean in ["onion", "tomato"]
        has_placeholder = not self.crops_cfg.get(crop_clean, {}).get("spoilage", {}).get("source", "PLACEHOLDER").startswith("PLACEHOLDER")
        conf_label, conf_score = compute_confidence(
            dq_score=0.85 if not is_synth else 0.40,
            model_interval_width=180.0,
            modal_price=baseline_price,
            is_placeholder=(not has_placeholder),
            config=self.config.as_dict(),
        )

        # Decision engine
        result: DecisionResult = decide(
            options=options,
            crop=crop_clean,
            crops_config=self.crops_cfg,
            trader_offer_per_q=trader_offer_per_q,
            cash_deadline_days=cash_deadline_days,
            shock_detected=False,
            confidence_score=conf_score,
            confidence_label=conf_label,
            forecast_usable=forecast_usable,
            decision_params=self.decision_params,
        )

        return result.to_api_response()
