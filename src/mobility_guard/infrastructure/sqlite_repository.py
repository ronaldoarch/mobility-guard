from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from mobility_guard.application.exceptions import DuplicateTransactionError
from mobility_guard.domain.models import (
    AnomalyAnalysis,
    AnomalyKind,
    AnomalyReason,
    EnrichmentStatus,
    StoredTransaction,
    Transaction,
    TransactionCategory,
)


class SQLiteTransactionRepository:
    """Small production-like adapter; the application only depends on its port."""

    def __init__(self, database_path: str) -> None:
        self._database_path = database_path
        self._lock = threading.Lock()
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            database_path,
            check_same_thread=False,
            isolation_level=None,
            timeout=5.0,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                external_id TEXT NOT NULL UNIQUE,
                customer_id TEXT NOT NULL,
                amount TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                category TEXT NOT NULL,
                merchant TEXT NOT NULL,
                anomaly_score REAL NOT NULL,
                anomaly_threshold REAL NOT NULL,
                anomaly_reasons TEXT NOT NULL,
                anomaly_explanation TEXT NOT NULL,
                enrichment_status TEXT NOT NULL DEFAULT 'skipped',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            str(row["name"])
            for row in self._connection.execute("PRAGMA table_info(transactions)").fetchall()
        }
        if "enrichment_status" not in columns:
            self._connection.execute(
                "ALTER TABLE transactions "
                "ADD COLUMN enrichment_status TEXT NOT NULL DEFAULT 'skipped'"
            )
        self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_customer_occurred
            ON transactions(customer_id, occurred_at DESC)
            """
        )

    def add(self, item: StoredTransaction) -> None:
        transaction = item.transaction
        analysis = item.analysis
        reasons = [
            {
                "kind": reason.kind.value,
                "weight": reason.weight,
                "message": reason.message,
            }
            for reason in analysis.reasons
        ]
        try:
            with self._lock, self._connection:
                self._connection.execute(
                    """
                    INSERT INTO transactions (
                        id, external_id, customer_id, amount, occurred_at, category,
                        merchant, anomaly_score, anomaly_threshold, anomaly_reasons,
                        anomaly_explanation, enrichment_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(transaction.id),
                        transaction.external_id,
                        transaction.customer_id,
                        str(transaction.amount),
                        transaction.occurred_at_utc.isoformat(),
                        transaction.category.value,
                        transaction.merchant,
                        analysis.score,
                        analysis.threshold,
                        json.dumps(reasons, ensure_ascii=False),
                        analysis.explanation,
                        item.enrichment_status.value,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateTransactionError(
                f"transaction {transaction.external_id!r} already exists"
            ) from exc

    def get_by_external_id(self, external_id: str) -> StoredTransaction | None:
        row = self._connection.execute(
            "SELECT * FROM transactions WHERE external_id = ?", (external_id,)
        ).fetchone()
        return self._to_item(row) if row is not None else None

    def list_by_customer(
        self, customer_id: str, *, limit: int = 100
    ) -> list[StoredTransaction]:
        rows = self._connection.execute(
            """
            SELECT * FROM (
                SELECT * FROM transactions
                WHERE customer_id = ?
                ORDER BY occurred_at DESC
                LIMIT ?
            ) recent
            ORDER BY occurred_at ASC
            """,
            (customer_id, limit),
        ).fetchall()
        return [self._to_item(row) for row in rows]

    def count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS total FROM transactions").fetchone()
        return int(row["total"])

    def healthcheck(self) -> bool:
        try:
            self._connection.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return False
        return True

    def update_enrichment(
        self,
        external_id: str,
        *,
        explanation: str,
        status: EnrichmentStatus,
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                UPDATE transactions
                SET anomaly_explanation = ?, enrichment_status = ?
                WHERE external_id = ?
                """,
                (explanation, status.value, external_id),
            )

    def close(self) -> None:
        self._connection.close()

    @staticmethod
    def _to_item(row: sqlite3.Row) -> StoredTransaction:
        reasons_data = json.loads(str(row["anomaly_reasons"]))
        reasons = tuple(
            AnomalyReason(
                kind=AnomalyKind(reason["kind"]),
                weight=float(reason["weight"]),
                message=str(reason["message"]),
            )
            for reason in reasons_data
        )
        transaction = Transaction(
            id=UUID(str(row["id"])),
            external_id=str(row["external_id"]),
            customer_id=str(row["customer_id"]),
            amount=Decimal(str(row["amount"])),
            occurred_at=datetime.fromisoformat(str(row["occurred_at"])),
            category=TransactionCategory(str(row["category"])),
            merchant=str(row["merchant"]),
        )
        analysis = AnomalyAnalysis(
            score=float(row["anomaly_score"]),
            threshold=float(row["anomaly_threshold"]),
            reasons=reasons,
            explanation=str(row["anomaly_explanation"]),
        )
        return StoredTransaction(
            transaction=transaction,
            analysis=analysis,
            enrichment_status=EnrichmentStatus(str(row["enrichment_status"])),
        )
