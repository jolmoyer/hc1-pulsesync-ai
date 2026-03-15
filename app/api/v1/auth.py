from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DBSession
from app.domain.auth.service import AuthService
from app.schemas.agent import AgentCreate, AgentResponse
from app.schemas.auth import AccessTokenResponse, LoginRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/bootstrap", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap(payload: AgentCreate, db: DBSession) -> AgentResponse:
    """Create the first admin agent. Returns 409 if any agent already exists."""
    service = AuthService(db)
    agents = await service.list_agents(page=1, page_size=1)
    if agents.total > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bootstrap not allowed: agents already exist",
        )
    payload.role = "admin"
    return await service.create_agent(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DBSession) -> TokenResponse:
    """Authenticate an agent and return JWT access + refresh tokens."""
    service = AuthService(db)
    result = await service.login(payload.email, payload.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return result


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(payload: RefreshRequest, db: DBSession) -> AccessTokenResponse:
    """Exchange a valid refresh token for a new access token."""
    service = AuthService(db)
    result = await service.refresh_access_token(payload.refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, db: DBSession) -> None:
    """Invalidate a refresh token."""
    service = AuthService(db)
    await service.logout(payload.refresh_token)
