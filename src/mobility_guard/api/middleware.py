from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "mobility_guard_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "mobility_guard_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))[:128]
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(elapsed)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
            request.method,
            path,
            response.status_code,
            elapsed * 1000,
            request_id,
        )
        return response

