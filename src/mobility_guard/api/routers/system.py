from fastapi import APIRouter, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from mobility_guard import __version__
from mobility_guard.api.dependencies import ContainerDependency
from mobility_guard.api.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(container: ContainerDependency, response: Response) -> HealthResponse:
    healthy = container.repository.healthcheck()
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if healthy else "degraded",
        database="up" if healthy else "down",
        version=__version__,
    )


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

