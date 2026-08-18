from fastapi import APIRouter

from mobility_guard.api.dependencies import ApiKeyDependency, ContainerDependency
from mobility_guard.api.schemas import BillingSummaryResponse

router = APIRouter(prefix="/v1/customers", tags=["customers"])


@router.get("/{customer_id}/billing-summary", response_model=BillingSummaryResponse)
def billing_summary(
    customer_id: str,
    container: ContainerDependency,
    _: ApiKeyDependency,
) -> BillingSummaryResponse:
    result = container.get_billing_summary.execute(customer_id)
    return BillingSummaryResponse.model_validate(result)

