"""
sell_smart.ingest.datagov_api
Stub ingestor for the data.gov.in Agmarknet variety-wise daily prices API.

UNVERIFIED: Current endpoint, key requirement, pagination and rate limits
have NOT been verified. Field names like `Min_x0020_Price` seen in sample
data suggest API origin. Needs DATAGOV_API_KEY env var.

This module implements the Ingestor interface and returns empty DataFrame
with the correct schema until the API is verified and an API key is provided.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from sellsmart.ingest.base import Ingestor
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

# UNVERIFIED: endpoint and field names
_API_BASE = "https://api.data.gov.in/resource/"  # UNVERIFIED
_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"  # UNVERIFIED — Agmarknet variety-wise


class DataGovAPIIngestor(Ingestor):
    source_name = "datagov_agmarknet_live"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("DATAGOV_API_KEY", "")

    def ingest(self, output_dir: Path) -> pd.DataFrame:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not self.api_key:
            logger.warning(
                "DATAGOV_API_KEY not set. DataGovAPIIngestor returning empty DataFrame. "
                "Set env var DATAGOV_API_KEY to enable live feed."
            )
            return pd.DataFrame(
                columns=[
                    "district_name", "market_name", "commodity", "variety",
                    "grade", "min_price", "max_price", "modal_price",
                    "price_date", "state", "source", "ingested_at",
                ]
            )

        # UNVERIFIED: API call below is a stub. Verify endpoint and pagination.
        try:
            import httpx  # type: ignore

            url = f"{_API_BASE}{_RESOURCE_ID}"
            params = {
                "api-key": self.api_key,
                "format": "json",
                "limit": 1000,
                "offset": 0,
            }
            logger.warning("DataGovAPIIngestor: API call is UNVERIFIED. Endpoint may differ.")
            resp = httpx.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            records = data.get("records", [])
            df = pd.DataFrame(records)
            # UNVERIFIED: field name mapping — sample showed Min_x0020_Price etc.
            logger.warning(
                f"DataGovAPIIngestor fetched {len(df)} rows. "
                "Field mapping is UNVERIFIED — check column names before use."
            )
            out_path = output_dir / "datagov_raw.parquet"
            df.to_parquet(out_path, index=False)
            return df
        except Exception as e:
            logger.error(f"DataGovAPIIngestor failed: {e}")
            return pd.DataFrame()
