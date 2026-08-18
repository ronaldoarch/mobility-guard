from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from mobility_guard.domain.models import (
    AnomalyAnalysis,
    AnomalyKind,
    AnomalyReason,
    EnrichmentStatus,
    StoredTransaction,
    Transaction,
    TransactionCategory,
)
from mobility_guard.infrastructure.sqlalchemy_repository import (
    SQLAlchemyTransactionRepository,
)


def test_sqlalchemy_repository_round_trip_and_enrichment(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'adapter.db'}"
    repository = SQLAlchemyTransactionRepository(database_url, create_schema=True)
    item = StoredTransaction(
        transaction=Transaction(
            id=uuid4(),
            external_id="postgres-contract-001",
            customer_id="customer-db",
            amount=Decimal("29.90"),
            occurred_at=datetime(2026, 8, 17, 14, tzinfo=UTC),
            category=TransactionCategory.PARKING,
            merchant="Estacionamento Teste",
        ),
        analysis=AnomalyAnalysis(
            score=0.72,
            threshold=0.65,
            reasons=(
                AnomalyReason(
                    kind=AnomalyKind.HIGH_AMOUNT,
                    weight=0.72,
                    message="Valor acima do histórico.",
                ),
            ),
            explanation="Explicação inicial.",
        ),
        enrichment_status=EnrichmentStatus.PENDING,
    )

    repository.add(item)
    repository.update_enrichment(
        "postgres-contract-001",
        explanation="Explicação enriquecida.",
        status=EnrichmentStatus.COMPLETED,
    )
    stored = repository.get_by_external_id("postgres-contract-001")

    assert stored is not None
    assert stored.transaction.amount == Decimal("29.90")
    assert stored.analysis.explanation == "Explicação enriquecida."
    assert stored.enrichment_status is EnrichmentStatus.COMPLETED
    assert repository.count() == 1
    assert repository.healthcheck() is True
    repository.close()
