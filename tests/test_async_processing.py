from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from mobility_guard.application.use_cases import RecordTransaction
from mobility_guard.domain.anomaly_detector import RuleBasedAnomalyDetector
from mobility_guard.domain.models import (
    EnrichmentStatus,
    StoredTransaction,
    TransactionCategory,
)
from mobility_guard.infrastructure.sqlite_repository import SQLiteTransactionRepository


class FakePublisher:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.external_ids: list[str] = []
        self.should_fail = should_fail

    def publish(self, external_id: str) -> None:
        if self.should_fail:
            raise ConnectionError("queue unavailable")
        self.external_ids.append(external_id)


def record_with_publisher(
    database_path: Path, publisher: FakePublisher
) -> tuple[SQLiteTransactionRepository, StoredTransaction]:
    repository = SQLiteTransactionRepository(str(database_path))
    use_case = RecordTransaction(
        repository,
        RuleBasedAnomalyDetector(),
        job_publisher=publisher,
    )
    item = use_case.execute(
        external_id="async-001",
        customer_id="customer-async",
        amount=Decimal("12.50"),
        occurred_at=datetime(2026, 8, 17, 14, tzinfo=UTC),
        category=TransactionCategory.TOLL,
        merchant="Rodovia Assíncrona",
    )
    return repository, item


def test_publishes_explanation_job_after_persistence(tmp_path: Path) -> None:
    publisher = FakePublisher()
    repository, item = record_with_publisher(tmp_path / "queue.db", publisher)

    assert item.enrichment_status is EnrichmentStatus.PENDING
    assert publisher.external_ids == ["async-001"]
    stored = repository.get_by_external_id("async-001")
    assert stored is not None
    assert stored.enrichment_status is EnrichmentStatus.PENDING
    repository.close()


def test_marks_enrichment_failed_when_queue_is_unavailable(tmp_path: Path) -> None:
    repository, item = record_with_publisher(
        tmp_path / "queue-failure.db",
        FakePublisher(should_fail=True),
    )

    assert item.enrichment_status is EnrichmentStatus.FAILED
    stored = repository.get_by_external_id("async-001")
    assert stored is not None
    assert stored.enrichment_status is EnrichmentStatus.FAILED
    repository.close()
