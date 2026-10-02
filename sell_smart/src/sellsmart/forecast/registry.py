"""
sell_smart.forecast.registry
Model registry: save/load trained models with metadata.
"""
from __future__ import annotations

import joblib
import json
from datetime import datetime, timezone
from pathlib import Path

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """Save and load forecasting models with metadata."""

    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def save(self, model, name: str, metadata: dict | None = None) -> Path:
        path = self.model_dir / f"{name}.joblib"
        joblib.dump(model, path)
        meta = {
            "name": name,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "path": str(path),
            **(metadata or {}),
        }
        meta_path = self.model_dir / f"{name}.meta.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        logger.info(f"Model saved: {path}")
        return path

    def load(self, name: str):
        path = self.model_dir / f"{name}.joblib"
        if not path.exists():
            raise FileNotFoundError(f"No model found at {path}")
        return joblib.load(path)

    def list_models(self) -> list[dict]:
        metas = list(self.model_dir.glob("*.meta.json"))
        result = []
        for m in metas:
            with open(m) as f:
                result.append(json.load(f))
        return result
