import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import AdminAgent, CurrentAgent, DBSession
from app.domain.auth.service import AgentNotFoundError, AuthService
from app.schemas.agent import AgentCreate, AgentListResponse, AgentResponse, AgentUpdate

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents(
    db: DBSession,
    _: AdminAgent,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AgentListResponse:
    service = AuthService(db)
    return await service.list_agents(page=page, page_size=page_size)


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate, db: DBSession, _: AdminAgent
) -> AgentResponse:
    service = AuthService(db)
    try:
        return await service.create_agent(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: uuid.UUID, db: DBSession, _: CurrentAgent) -> AgentResponse:
    service = AuthService(db)
    try:
        return await service.get_agent(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID, payload: AgentUpdate, db: DBSession, _: AdminAgent
) -> AgentResponse:
    service = AuthService(db)
    try:
        return await service.update_agent(agent_id, payload)
    except AgentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_agent(
    agent_id: uuid.UUID, db: DBSession, _: AdminAgent
) -> None:
    """Soft-delete: sets is_active = False."""
    service = AuthService(db)
    try:
        await service.deactivate_agent(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
