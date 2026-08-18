from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from mobility_guard.domain.models import StoredTransaction, TransactionCategory

NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]


class RecordTransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: NonEmptyText
    customer_id: NonEmptyText
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    occurred_at: datetime
    category: TransactionCategory
    merchant: NonEmptyText


class AnomalyReasonResponse(BaseModel):
    kind: str
    weight: float
    message: str


class AnomalyResponse(BaseModel):
    is_anomaly: bool
    score: float
    threshold: float
    reasons: list[AnomalyReasonResponse]
    explanation: str


class TransactionResponse(BaseModel):
    id: UUID
    external_id: str
    customer_id: str
    amount: Decimal
    occurred_at: datetime
    category: TransactionCategory
    merchant: str
    enrichment_status: str
    anomaly: AnomalyResponse

    @classmethod
    def from_domain(cls, item: StoredTransaction) -> TransactionResponse:
        transaction = item.transaction
        analysis = item.analysis
        return cls(
            id=transaction.id,
            external_id=transaction.external_id,
            customer_id=transaction.customer_id,
            amount=transaction.amount,
            occurred_at=transaction.occurred_at,
            category=transaction.category,
            merchant=transaction.merchant,
            enrichment_status=item.enrichment_status.value,
            anomaly=AnomalyResponse(
                is_anomaly=analysis.is_anomaly,
                score=analysis.score,
                threshold=analysis.threshold,
                reasons=[
                    AnomalyReasonResponse(
                        kind=reason.kind.value,
                        weight=reason.weight,
                        message=reason.message,
                    )
                    for reason in analysis.reasons
                ],
                explanation=analysis.explanation,
            ),
        )


class BillingSummaryResponse(BaseModel):
    customer_id: str
    transaction_count: int
    anomaly_count: int
    total_amount: Decimal
    by_category: dict[str, Decimal]


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None
