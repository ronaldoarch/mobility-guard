from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class TransactionCategory(StrEnum):
    TOLL = "toll"
    PARKING = "parking"
    FUEL = "fuel"
    DRIVE_THRU = "drive_thru"


class AnomalyKind(StrEnum):
    HIGH_AMOUNT = "high_amount"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    UNUSUAL_HOUR = "unusual_hour"
    INSUFFICIENT_HISTORY = "insufficient_history"


class EnrichmentStatus(StrEnum):
    SKIPPED = "skipped"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Transaction:
    id: UUID
    external_id: str
    customer_id: str
    amount: Decimal
    occurred_at: datetime
    category: TransactionCategory
    merchant: str

    def __post_init__(self) -> None:
        if not self.external_id.strip():
            raise ValueError("external_id cannot be empty")
        if not self.customer_id.strip():
            raise ValueError("customer_id cannot be empty")
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        if not self.merchant.strip():
            raise ValueError("merchant cannot be empty")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must contain timezone information")

    @property
    def occurred_at_utc(self) -> datetime:
        return self.occurred_at.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class AnomalyReason:
    kind: AnomalyKind
    weight: float
    message: str


@dataclass(frozen=True, slots=True)
class AnomalyAnalysis:
    score: float
    threshold: float
    reasons: tuple[AnomalyReason, ...]
    explanation: str

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1")
        if not 0 <= self.threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")

    @property
    def is_anomaly(self) -> bool:
        return self.score >= self.threshold


@dataclass(frozen=True, slots=True)
class StoredTransaction:
    transaction: Transaction
    analysis: AnomalyAnalysis
    enrichment_status: EnrichmentStatus = EnrichmentStatus.SKIPPED
