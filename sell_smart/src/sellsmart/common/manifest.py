"""
sell_smart.common.manifest
Run manifest: row counts, hashes, metadata for each pipeline stage.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def data_hash(df: pd.DataFrame) -> str:
    """Deterministic hash of a DataFrame (column names + values)."""
    df_clean = df.copy()
    for col in df_clean.columns:
        if df_clean[col].dtype == "object":
            df_clean[col] = df_clean[col].astype(str)
    buf = pd.util.hash_pandas_object(df_clean, index=True).values.tobytes()
    return hashlib.sha256(buf).hexdigest()[:16]


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def write_manifest(
    stage: str,
    output_path: Path,
    df: pd.DataFrame,
    extra: dict[str, Any] | None = None,
    config_hash: str = "",
    seed: int = 42,
) -> dict:
    manifest = {
        "stage": stage,
        "output_path": str(output_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(df),
        "columns": list(df.columns),
        "config_hash": config_hash,
        "seed": seed,
        "data_hash": data_hash(df),
    }
    if df.index.dtype == "object" or hasattr(df, "date"):
        date_col = next((c for c in df.columns if "date" in c.lower()), None)
        if date_col:
            try:
                manifest["min_date"] = str(df[date_col].min())
                manifest["max_date"] = str(df[date_col].max())
            except Exception:
                pass
    if extra:
        manifest.update(extra)

    manifest_path = output_path.with_suffix(".manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def load_manifest(path: Path) -> dict:
    manifest_path = path.with_suffix(".manifest.json")
    if not manifest_path.exists():
        return {}
    with open(manifest_path) as f:
        return json.load(f)
