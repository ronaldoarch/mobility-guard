from pathlib import Path

from fastapi.testclient import TestClient

from mobility_guard.config import Settings
from mobility_guard.main import create_app


def make_client(database_path: Path, *, api_key: str | None = None) -> TestClient:
    settings = Settings(
        database_path=str(database_path),
        api_key=api_key,
        openai_api_key=None,
    )
    return TestClient(create_app(settings))


def transaction_payload(external_id: str = "tx-001") -> dict[str, object]:
    return {
        "external_id": external_id,
        "customer_id": "customer-001",
        "amount": "12.50",
        "occurred_at": "2026-08-17T14:30:00-03:00",
        "category": "toll",
        "merchant": "Rodovia SP-123 Km 42",
    }


def test_records_and_reads_transaction(tmp_path: Path) -> None:
    with make_client(tmp_path / "test.db") as client:
        created = client.post("/v1/transactions", json=transaction_payload())
        fetched = client.get("/v1/transactions/tx-001")

    assert created.status_code == 201
    assert created.json()["anomaly"]["is_anomaly"] is False
    assert fetched.status_code == 200
    assert fetched.json()["external_id"] == "tx-001"
    assert created.headers["x-request-id"]


def test_rejects_duplicate_external_id(tmp_path: Path) -> None:
    with make_client(tmp_path / "test.db") as client:
        client.post("/v1/transactions", json=transaction_payload())
        duplicate = client.post("/v1/transactions", json=transaction_payload())

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate_transaction"


def test_returns_billing_summary(tmp_path: Path) -> None:
    with make_client(tmp_path / "test.db") as client:
        client.post("/v1/transactions", json=transaction_payload("tx-001"))
        second = transaction_payload("tx-002")
        second["amount"] = "7.50"
        second["category"] = "parking"
        second["occurred_at"] = "2026-08-18T15:00:00-03:00"
        client.post("/v1/transactions", json=second)
        response = client.get("/v1/customers/customer-001/billing-summary")

    assert response.status_code == 200
    assert response.json() == {
        "customer_id": "customer-001",
        "transaction_count": 2,
        "anomaly_count": 0,
        "total_amount": "20.00",
        "by_category": {"toll": "12.50", "parking": "7.50"},
    }


def test_requires_configured_api_key(tmp_path: Path) -> None:
    with make_client(tmp_path / "test.db", api_key="secret") as client:
        unauthorized = client.post("/v1/transactions", json=transaction_payload())
        authorized = client.post(
            "/v1/transactions",
            json=transaction_payload(),
            headers={"X-API-Key": "secret"},
        )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 201


def test_health_endpoint(tmp_path: Path) -> None:
    with make_client(tmp_path / "test.db") as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

