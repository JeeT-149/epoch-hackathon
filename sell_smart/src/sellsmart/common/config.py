"""
sell_smart.common.config
Config loader: merges default.yaml with optional overrides, computes hashes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


_ROOT = Path(__file__).parents[3]  # sell_smart/


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class Config:
    """Thin wrapper around a merged YAML config dict."""

    def __init__(self, data: dict, config_hash: str):
        self._data = data
        self.config_hash = config_hash

    def get(self, *keys: str, default: Any = None) -> Any:
        node = self._data
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k, default)
        return node

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def as_dict(self) -> dict:
        return self._data

    def has_placeholders(self) -> bool:
        return "PLACEHOLDER" in json.dumps(self._data)

    def demo_ready(self) -> bool:
        return not self.has_placeholders()


def load_config(override_path: Path | None = None, config_dir: Path | None = None) -> Config:
    """Load default.yaml and optionally merge an override file."""
    if config_dir is None:
        config_dir = _ROOT / "config"

    default_path = config_dir / "default.yaml"
    with open(default_path) as f:
        data = yaml.safe_load(f)

    if override_path and override_path.exists():
        with open(override_path) as f:
            override = yaml.safe_load(f) or {}
        data = _deep_merge(data, override)

    config_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]
    return Config(data, config_hash)


def load_crops_config(config_dir: Path | None = None) -> dict:
    if config_dir is None:
        config_dir = _ROOT / "config"
    with open(config_dir / "crops.yaml") as f:
        return yaml.safe_load(f)["crops"]


def load_commodity_map(config_dir: Path | None = None) -> dict:
    if config_dir is None:
        config_dir = _ROOT / "config"
    with open(config_dir / "commodity_map.yaml") as f:
        return yaml.safe_load(f)["crops"]
