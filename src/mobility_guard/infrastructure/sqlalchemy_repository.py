from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    create_engine,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine, RowMapping
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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

metadata = MetaData()

transactions_table = Table(
    "transactions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("external_id", String(120), nullable=False, unique=True),
    Column("customer_id", String(120), nullable=False),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("category", String(40), nullable=False),
    Column("merchant", String(120), nullable=False),
    Column("anomaly_score", Float, nullable=False),
    Column("anomaly_threshold", Float, nullable=False),
    Column("anomaly_reasons", JSON, nullable=False),
    Column("anomaly_explanation", Text, nullable=False),
    Column("enrichment_status", String(20), nullable=False, server_default="skipped"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Index("idx_transactions_customer_occurred", "customer_id", "occurred_at"),
)


class SQLAlchemyTransactionRepository:
    """PostgreSQL adapter with pooled connections and explicit transactions."""

    def __init__(self, database_url: str, *, create_schema: bool = False) -> None:
        self._engine: Engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        if create_schema:
            metadata.create_all(self._engine)

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
            with self._engine.begin() as connection:
                connection.execute(
                    insert(transactions_table).values(
                        id=str(transaction.id),
                        external_id=transaction.external_id,
                        customer_id=transaction.customer_id,
                        amount=transaction.amount,
                        occurred_at=transaction.occurred_at_utc,
                        category=transaction.category.value,
                        merchant=transaction.merchant,
                        anomaly_score=analysis.score,
                        anomaly_threshold=analysis.threshold,
                        anomaly_reasons=reasons,
                        anomaly_explanation=analysis.explanation,
                        enrichment_status=item.enrichment_status.value,
                    )
                )
        except IntegrityError as exc:
            raise DuplicateTransactionError(
                f"transaction {transaction.external_id!r} already exists"
            ) from exc

    def get_by_external_id(self, external_id: str) -> StoredTransaction | None:
        query = select(transactions_table).where(
            transactions_table.c.external_id == external_id
        )
        with self._engine.connect() as connection:
            row = connection.execute(query).mappings().one_or_none()
        return self._to_item(row) if row is not None else None

    def list_by_customer(
        self, customer_id: str, *, limit: int = 100
    ) -> list[StoredTransaction]:
        recent = (
            select(transactions_table)
            .where(transactions_table.c.customer_id == customer_id)
            .order_by(transactions_table.c.occurred_at.desc())
            .limit(limit)
            .subquery()
        )
        query = select(recent).order_by(recent.c.occurred_at.asc())
        with self._engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [self._to_item(row) for row in rows]

    def count(self) -> int:
        with self._engine.connect() as connection:
            result = connection.scalar(select(func.count()).select_from(transactions_table))
        return int(result or 0)

    def healthcheck(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(select(1))
        except SQLAlchemyError:
            return False
        return True

    def update_enrichment(
        self,
        external_id: str,
        *,
        explanation: str,
        status: EnrichmentStatus,
    ) -> None:
        statement = (
            update(transactions_table)
            .where(transactions_table.c.external_id == external_id)
            .values(
                anomaly_explanation=explanation,
                enrichment_status=status.value,
            )
        )
        with self._engine.begin() as connection:
            connection.execute(statement)

    def close(self) -> None:
        self._engine.dispose()

    @staticmethod
    def _to_item(row: RowMapping) -> StoredTransaction:
        raw_reasons: list[dict[str, Any]] = row["anomaly_reasons"]
        reasons = tuple(
            AnomalyReason(
                kind=AnomalyKind(reason["kind"]),
                weight=float(reason["weight"]),
                message=str(reason["message"]),
            )
            for reason in raw_reasons
        )
        occurred_at: datetime = row["occurred_at"]
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        return StoredTransaction(
            transaction=Transaction(
                id=UUID(str(row["id"])),
                external_id=str(row["external_id"]),
                customer_id=str(row["customer_id"]),
                amount=Decimal(str(row["amount"])),
                occurred_at=occurred_at,
                category=TransactionCategory(str(row["category"])),
                merchant=str(row["merchant"]),
            ),
            analysis=AnomalyAnalysis(
                score=float(row["anomaly_score"]),
                threshold=float(row["anomaly_threshold"]),
                reasons=reasons,
                explanation=str(row["anomaly_explanation"]),
            ),
            enrichment_status=EnrichmentStatus(str(row["enrichment_status"])),
        )
