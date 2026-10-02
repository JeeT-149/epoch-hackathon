"""
sell_smart.ingest.base
Pluggable Ingestor interface so primary data source can change without
touching downstream code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd


class Ingestor(ABC):
    """Base class for all data ingestors."""

    source_name: str = "unknown"

    @abstractmethod
    def ingest(self, output_dir: Path) -> pd.DataFrame:
        """
        Load raw data, write to output_dir as parquet, return DataFrame.
        Must add columns: source, ingested_at.
        Must NOT modify data — raw bronze layer only.
        """

    def validate_schema(self, df: pd.DataFrame) -> None:
        """Optional: raise ValueError if required columns are missing."""
