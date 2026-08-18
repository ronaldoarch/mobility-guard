from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from mobility_guard.application.exceptions import DuplicateTransactionError
from mobility_guard.application.ports import (
    ExplanationJobPublisher,
    ExplanationProvider,
    TransactionRepository,
)
from mobility_guard.domain.anomaly_detector import RuleBasedAnomalyDetector
from mobility_guard.domain.models import (
    AnomalyAnalysis,
    EnrichmentStatus,
    StoredTransaction,
    Transaction,
    TransactionCategory,
)


class RecordTransaction:
    def __init__(
        self,
        repository: TransactionRepository,
        detector: RuleBasedAnomalyDetector,
        explanation_provider: ExplanationProvider | None = None,
        job_publisher: ExplanationJobPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._detector = detector
        self._explanation_provider = explanation_provider
        self._job_publisher = job_publisher

    def execute(
        self,
        *,
        external_id: str,
        customer_id: str,
        amount: Decimal,
        occurred_at: datetime,
        category: TransactionCategory,
        merchant: str,
        transaction_id: UUID | None = None,
    ) -> StoredTransaction:
        if self._repository.get_by_external_id(external_id) is not None:
            raise DuplicateTransactionError(f"transaction {external_id!r} already exists")

        transaction = Transaction(
            id=transaction_id or uuid4(),
            external_id=external_id,
            customer_id=customer_id,
            amount=amount,
            occurred_at=occurred_at,
            category=category,
            merchant=merchant,
        )
        history = self._repository.list_by_customer(customer_id, limit=100)
        analysis = self._detector.analyze(transaction, history)
        analysis = self._with_generated_explanation(transaction, analysis)
        enrichment_status = (
            EnrichmentStatus.PENDING if self._job_publisher else EnrichmentStatus.SKIPPED
        )
        item = StoredTransaction(
            transaction=transaction,
            analysis=analysis,
            enrichment_status=enrichment_status,
        )
        self._repository.add(item)
        if self._job_publisher is not None:
            try:
                self._job_publisher.publish(external_id)
            except Exception:
                self._repository.update_enrichment(
                    external_id,
                    explanation=analysis.explanation,
                    status=EnrichmentStatus.FAILED,
                )
                item = replace(item, enrichment_status=EnrichmentStatus.FAILED)
        return item

    def _with_generated_explanation(
        self, transaction: Transaction, analysis: AnomalyAnalysis
    ) -> AnomalyAnalysis:
        if self._explanation_provider is None:
            return analysis
        try:
            explanation = self._explanation_provider.explain(transaction, analysis)
        except Exception:  # The deterministic result remains available if the provider is down.
            return analysis
        return replace(analysis, explanation=explanation)


class GetBillingSummary:
    def __init__(self, repository: TransactionRepository) -> None:
        self._repository = repository

    def execute(self, customer_id: str) -> dict[str, object]:
        items = self._repository.list_by_customer(customer_id, limit=500)
        total = sum((item.transaction.amount for item in items), start=Decimal("0"))
        anomalies = sum(item.analysis.is_anomaly for item in items)
        by_category: dict[str, Decimal] = {}
        for item in items:
            category = item.transaction.category.value
            current = by_category.get(category, Decimal("0"))
            by_category[category] = current + item.transaction.amount
        return {
            "customer_id": customer_id,
            "transaction_count": len(items),
            "anomaly_count": anomalies,
            "total_amount": total,
            "by_category": by_category,
        }
