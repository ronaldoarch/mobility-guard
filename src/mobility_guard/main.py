from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from mobility_guard import __version__
from mobility_guard.api.middleware import RequestContextMiddleware
from mobility_guard.api.routers import customers, system, transactions
from mobility_guard.api.schemas import ErrorResponse
from mobility_guard.application.exceptions import (
    DuplicateTransactionError,
    TransactionNotFoundError,
)
from mobility_guard.config import Settings, get_settings
from mobility_guard.container import build_container


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        container = build_container(resolved_settings)
        application.state.container = container
        try:
            yield
        finally:
            container.repository.close()

    logging.basicConfig(
        level=resolved_settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    application = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        description=(
            "API para registrar cobranças de mobilidade, detectar anomalias "
            "e gerar resumos explicáveis."
        ),
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.add_middleware(RequestContextMiddleware)
    application.include_router(system.router)
    application.include_router(transactions.router)
    application.include_router(customers.router)

    @application.exception_handler(DuplicateTransactionError)
    async def duplicate_handler(
        request: Request, exc: DuplicateTransactionError
    ) -> JSONResponse:
        body = ErrorResponse(
            code="duplicate_transaction",
            message=str(exc),
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=body.model_dump(),
        )

    @application.exception_handler(TransactionNotFoundError)
    async def not_found_handler(
        request: Request, exc: TransactionNotFoundError
    ) -> JSONResponse:
        body = ErrorResponse(
            code="transaction_not_found",
            message=f"transaction {exc} was not found",
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=body.model_dump(),
        )

    return application


app = create_app()
