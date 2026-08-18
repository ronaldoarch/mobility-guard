from datetime import UTC, datetime, timedelta
from decimal import Decimal

from mobility_guard.config import get_settings
from mobility_guard.container import build_container
from mobility_guard.domain.models import TransactionCategory


def main() -> None:
    container = build_container(get_settings())
    base = datetime(2026, 8, 10, 13, tzinfo=UTC)
    amounts = ["10.00", "10.50", "9.80", "11.00", "10.20", "48.90"]
    for index, amount in enumerate(amounts, start=1):
        external_id = f"demo-{index:03d}"
        if container.repository.get_by_external_id(external_id) is not None:
            continue
        item = container.record_transaction.execute(
            external_id=external_id,
            customer_id="demo-customer",
            amount=Decimal(amount),
            occurred_at=base + timedelta(days=index),
            category=TransactionCategory.TOLL,
            merchant="Rodovia Demo Km 42",
        )
        print(external_id, item.analysis.score, item.analysis.is_anomaly)


if __name__ == "__main__":
    main()

