from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from mobility_guard.container import Container


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDependency = Annotated[Container, Depends(get_container)]


def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    expected: str | None = request.app.state.settings.api_key
    if expected and (x_api_key is None or not secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )


ApiKeyDependency = Annotated[None, Depends(require_api_key)]

