from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from mobility_guard.domain.anomaly_detector import RuleBasedAnomalyDetector
from mobility_guard.domain.models import (
    AnomalyAnalysis,
    StoredTransaction,
    Transaction,
    TransactionCategory,
)


def make_transaction(
    *,
    external_id: str,
    amount: str,
    occurred_at: datetime,
    merchant: str = "Pedágio Norte",
) -> Transaction:
    return Transaction(
        id=uuid4(),
        external_id=external_id,
        customer_id="customer-1",
        amount=Decimal(amount),
        occurred_at=occurred_at,
        category=TransactionCategory.TOLL,
        merchant=merchant,
    )


def stored(transaction: Transaction) -> StoredTransaction:
    return StoredTransaction(
        transaction=transaction,
        analysis=AnomalyAnalysis(score=0, threshold=0.65, reasons=(), explanation="ok"),
    )


def test_marks_possible_duplicate_as_anomaly() -> None:
    now = datetime(2026, 8, 17, 14, tzinfo=UTC)
    previous = stored(
        make_transaction(external_id="tx-1", amount="12.50", occurred_at=now)
    )
    candidate = make_transaction(
        external_id="tx-2",
        amount="12.50",
        occurred_at=now + timedelta(minutes=2),
    )

    result = RuleBasedAnomalyDetector().analyze(candidate, [previous])

    assert result.is_anomaly is True
    assert result.score == 0.82
    assert result.reasons[0].kind.value == "possible_duplicate"


def test_marks_large_amount_against_stable_history() -> None:
    now = datetime(2026, 8, 17, 14, tzinfo=UTC)
    history = [
        stored(
            make_transaction(
                external_id=f"tx-{index}",
                amount="10.00",
                occurred_at=now + timedelta(days=index),
            )
        )
        for index in range(4)
    ]
    candidate = make_transaction(
        external_id="tx-high",
        amount="35.00",
        occurred_at=now + timedelta(days=5),
    )

    result = RuleBasedAnomalyDetector().analyze(candidate, history)

    assert result.is_anomaly is True
    assert result.score == 0.72


def test_regular_transaction_is_not_anomaly() -> None:
    now = datetime(2026, 8, 17, 14, tzinfo=UTC)
    history = [
        stored(
            make_transaction(
                external_id=f"tx-{index}",
                amount=amount,
                occurred_at=now + timedelta(days=index),
            )
        )
        for index, amount in enumerate(["9.50", "10.00", "10.50", "11.00"])
    ]
    candidate = make_transaction(
        external_id="tx-normal",
        amount="10.25",
        occurred_at=now + timedelta(days=5),
    )

    result = RuleBasedAnomalyDetector().analyze(candidate, history)

    assert result.is_anomaly is False
    assert result.score == 0

