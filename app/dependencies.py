from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.auth.service import AuthService

_bearer = HTTPBearer(auto_error=True)


async def get_current_agent(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Validate JWT and return the decoded payload.
    Raises 401 on invalid/expired tokens."""
    auth_service = AuthService(db)
    payload = await auth_service.verify_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def require_admin(
    current_agent: Annotated[dict, Depends(get_current_agent)],
) -> dict:
    """Restrict endpoint to agents with the 'admin' role."""
    if current_agent.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_agent


# Convenience type aliases for route signatures
DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentAgent = Annotated[dict, Depends(get_current_agent)]
AdminAgent = Annotated[dict, Depends(require_admin)]
