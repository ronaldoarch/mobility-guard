from typing import Annotated

from fastapi import APIRouter, Query, status

from mobility_guard.api.dependencies import ApiKeyDependency, ContainerDependency
from mobility_guard.api.schemas import RecordTransactionRequest, TransactionResponse

router = APIRouter(
    prefix="/v1/transactions",
    tags=["transactions"],
)


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def record_transaction(
    payload: RecordTransactionRequest,
    container: ContainerDependency,
    _: ApiKeyDependency,
) -> TransactionResponse:
    item = container.record_transaction.execute(
        external_id=payload.external_id,
        customer_id=payload.customer_id,
        amount=payload.amount,
        occurred_at=payload.occurred_at,
        category=payload.category,
        merchant=payload.merchant,
    )
    return TransactionResponse.from_domain(item)


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    container: ContainerDependency,
    _: ApiKeyDependency,
    customer_id: Annotated[str, Query(min_length=1, max_length=120)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[TransactionResponse]:
    items = container.repository.list_by_customer(customer_id, limit=limit)
    return [TransactionResponse.from_domain(item) for item in items]


@router.get("/{external_id}", response_model=TransactionResponse)
def get_transaction(
    external_id: str,
    container: ContainerDependency,
    _: ApiKeyDependency,
) -> TransactionResponse:
    item = container.repository.get_by_external_id(external_id)
    if item is None:
        from mobility_guard.application.exceptions import TransactionNotFoundError

        raise TransactionNotFoundError(external_id)
    return TransactionResponse.from_domain(item)

