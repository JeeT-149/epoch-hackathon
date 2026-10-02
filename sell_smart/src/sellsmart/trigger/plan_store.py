"""
sell_smart.trigger.plan_store
SQLite-backed persistent plan store and transactional outbox for farmer selling plans.
Enforces idempotency and anti-leakage next-open-day execution (Step 5).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SellingPlan:
    plan_id: str
    farmer_id: str
    crop: str
    mandi_id: str
    quantity_q: float
    creation_date: date
    target_price: float
    stop_loss_price: float
    cash_deadline_date: date
    status: str = "WATCHING"  # WATCHING | TRIGGERED_SELL | EXECUTED | DEADLINE_REACHED | SUSPENDED_SHOCK
    triggered_date: Optional[date] = None
    executed_date: Optional[date] = None
    executed_price: Optional[float] = None
    net_realized_return_per_q: Optional[float] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["creation_date"] = str(self.creation_date)
        d["cash_deadline_date"] = str(self.cash_deadline_date)
        d["triggered_date"] = str(self.triggered_date) if self.triggered_date else None
        d["executed_date"] = str(self.executed_date) if self.executed_date else None
        return d


class PlanStore:
    """
    SQLite persistent plan store with outbox table and idempotent transactions.
    """

    def __init__(self, db_path: Path | str = ":memory:"):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    farmer_id TEXT NOT NULL,
                    crop TEXT NOT NULL,
                    mandi_id TEXT NOT NULL,
                    quantity_q REAL NOT NULL,
                    creation_date TEXT NOT NULL,
                    target_price REAL NOT NULL,
                    stop_loss_price REAL NOT NULL,
                    cash_deadline_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    triggered_date TEXT,
                    executed_date TEXT,
                    executed_price REAL,
                    net_realized_return_per_q REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Outbox events table with UNIQUE constraint for guaranteed idempotency
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS outbox_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0,
                    UNIQUE(plan_id, event_date, event_type)
                );
            """)

    def save_plan(self, plan: SellingPlan) -> None:
        """Insert or replace a selling plan."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO plans (
                    plan_id, farmer_id, crop, mandi_id, quantity_q,
                    creation_date, target_price, stop_loss_price, cash_deadline_date,
                    status, triggered_date, executed_date, executed_price,
                    net_realized_return_per_q, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(plan_id) DO UPDATE SET
                    status=excluded.status,
                    triggered_date=excluded.triggered_date,
                    executed_date=excluded.executed_date,
                    executed_price=excluded.executed_price,
                    net_realized_return_per_q=excluded.net_realized_return_per_q,
                    notes=excluded.notes,
                    updated_at=CURRENT_TIMESTAMP;
            """, (
                plan.plan_id,
                plan.farmer_id,
                plan.crop,
                plan.mandi_id,
                plan.quantity_q,
                str(plan.creation_date),
                plan.target_price,
                plan.stop_loss_price,
                str(plan.cash_deadline_date),
                plan.status,
                str(plan.triggered_date) if plan.triggered_date else None,
                str(plan.executed_date) if plan.executed_date else None,
                plan.executed_price,
                plan.net_realized_return_per_q,
                plan.notes,
            ))

    def get_plan(self, plan_id: str) -> Optional[SellingPlan]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM plans WHERE plan_id = ?", (plan_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_plan(row)

    def get_active_plans(self) -> List[SellingPlan]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM plans
            WHERE status IN ('WATCHING', 'TRIGGERED_SELL', 'DEADLINE_REACHED')
            ORDER BY creation_date ASC
        """)
        return [self._row_to_plan(row) for row in cur.fetchall()]

    def emit_outbox_event(
        self,
        plan_id: str,
        event_date: date,
        event_type: str,
        payload: Dict[str, Any],
    ) -> bool:
        """
        Emit event into transactional outbox.
        Idempotent: Uses INSERT OR IGNORE on (plan_id, event_date, event_type).
        Returns True if newly inserted, False if already existed.
        """
        with self.conn:
            cur = self.conn.execute("""
                INSERT OR IGNORE INTO outbox_events (
                    plan_id, event_date, event_type, payload
                ) VALUES (?, ?, ?, ?)
            """, (
                plan_id,
                str(event_date),
                event_type,
                json.dumps(payload),
            ))
            return cur.rowcount > 0

    def get_outbox_events(self, plan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        if plan_id:
            cur.execute("SELECT * FROM outbox_events WHERE plan_id = ? ORDER BY event_id ASC", (plan_id,))
        else:
            cur.execute("SELECT * FROM outbox_events ORDER BY event_id ASC")
        rows = cur.fetchall()
        results = []
        for r in rows:
            results.append({
                "event_id": r["event_id"],
                "plan_id": r["plan_id"],
                "event_date": r["event_date"],
                "event_type": r["event_type"],
                "payload": json.loads(r["payload"]),
                "created_at": r["created_at"],
                "processed": r["processed"],
            })
        return results

    def _row_to_plan(self, row: sqlite3.Row) -> SellingPlan:
        return SellingPlan(
            plan_id=row["plan_id"],
            farmer_id=row["farmer_id"],
            crop=row["crop"],
            mandi_id=row["mandi_id"],
            quantity_q=row["quantity_q"],
            creation_date=datetime.strptime(row["creation_date"], "%Y-%m-%d").date(),
            target_price=row["target_price"],
            stop_loss_price=row["stop_loss_price"],
            cash_deadline_date=datetime.strptime(row["cash_deadline_date"], "%Y-%m-%d").date(),
            status=row["status"],
            triggered_date=datetime.strptime(row["triggered_date"], "%Y-%m-%d").date() if row["triggered_date"] else None,
            executed_date=datetime.strptime(row["executed_date"], "%Y-%m-%d").date() if row["executed_date"] else None,
            executed_price=row["executed_price"],
            net_realized_return_per_q=row["net_realized_return_per_q"],
            notes=row["notes"] or "",
        )

    def close(self) -> None:
        self.conn.close()
