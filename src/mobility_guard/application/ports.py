from __future__ import annotations

from typing import Protocol

from mobility_guard.domain.models import (
    AnomalyAnalysis,
    EnrichmentStatus,
    StoredTransaction,
    Transaction,
)


class TransactionRepository(Protocol):
    def add(self, item: StoredTransaction) -> None: ...

    def get_by_external_id(self, external_id: str) -> StoredTransaction | None: ...

    def list_by_customer(
        self, customer_id: str, *, limit: int = 100
    ) -> list[StoredTransaction]: ...

    def count(self) -> int: ...

    def healthcheck(self) -> bool: ...

    def update_enrichment(
        self,
        external_id: str,
        *,
        explanation: str,
        status: EnrichmentStatus,
    ) -> None: ...

    def close(self) -> None: ...


class ExplanationProvider(Protocol):
    def explain(self, transaction: Transaction, analysis: AnomalyAnalysis) -> str: ...


class ExplanationJobPublisher(Protocol):
    def publish(self, external_id: str) -> None: ...
