"""
sell_smart.ingest.kaggle_csv
Ingestor for the Kaggle Agmarknet CSV dataset.

Known schema (verified from actual file):
    Sl no., District Name, Market Name, Commodity, Variety, Grade,
    Min Price (Rs./Quintal), Max Price (Rs./Quintal),
    Modal Price (Rs./Quintal), Price Date, State

NOTE: The Kaggle dataset has a 'State' column — the PRD anticipated its
      absence for Maharashtra-only but this file covers 8 states.
      See docs/DECISIONS.md for the consequence.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from sellsmart.ingest.base import Ingestor
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

COLUMN_MAP = {
    "Sl no.": "sl_no",
    "District Name": "district_name",
    "Market Name": "market_name",
    "Commodity": "commodity",
    "Variety": "variety",
    "Grade": "grade",
    "Min Price (Rs./Quintal)": "min_price",
    "Max Price (Rs./Quintal)": "max_price",
    "Modal Price (Rs./Quintal)": "modal_price",
    "Price Date": "price_date",
    "State": "state",
}

REQUIRED_COLUMNS = list(COLUMN_MAP.keys())


class KaggleCSVIngestor(Ingestor):
    source_name = "kaggle_agmarknet_2024_2025"

    def __init__(self, csv_path: Path):
        self.csv_path = Path(csv_path)

    def ingest(self, output_dir: Path) -> pd.DataFrame:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Ingesting {self.csv_path} ...")
        df = pd.read_csv(self.csv_path, low_memory=False)

        self.validate_schema(df)

        df = df.rename(columns=COLUMN_MAP)
        df["source"] = self.source_name
        df["ingested_at"] = datetime.now(timezone.utc).isoformat()

        out_path = output_dir / "agmarknet_raw.parquet"
        df.to_parquet(out_path, index=False)
        logger.info(f"Wrote {len(df):,} rows to {out_path}")
        return df

    def validate_schema(self, df: pd.DataFrame) -> None:
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"KaggleCSVIngestor: missing expected columns: {missing}\n"
                f"Found: {list(df.columns)}"
            )
        logger.info(f"Schema validated. Columns: {list(df.columns)}")
