import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentAgent, DBSession
from app.domain.queue.service import QueueItemNotFoundError, QueueService
from app.schemas.queue import QueueItemResponse, QueueItemUpdate, QueueListResponse

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=QueueListResponse)
async def list_queue(
    db: DBSession,
    _: CurrentAgent,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    assigned_to: uuid.UUID | None = Query(default=None),
    classification: str | None = Query(default=None),
) -> QueueListResponse:
    """List queue items with optional filters."""
    service = QueueService(db)
    return await service.list_items(
        page=page,
        page_size=page_size,
        status_filter=status,
        assigned_to=assigned_to,
        classification_filter=classification,
    )


@router.get("/{item_id}", response_model=QueueItemResponse)
async def get_queue_item(
    item_id: uuid.UUID, db: DBSession, _: CurrentAgent
) -> QueueItemResponse:
    service = QueueService(db)
    try:
        return await service.get_item(item_id)
    except QueueItemNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")


@router.patch("/{item_id}", response_model=QueueItemResponse)
async def update_queue_item(
    item_id: uuid.UUID,
    payload: QueueItemUpdate,
    db: DBSession,
    agent: CurrentAgent,
) -> QueueItemResponse:
    """Update queue item status or add reviewer notes."""
    service = QueueService(db)
    try:
        return await service.update_item(item_id=item_id, payload=payload, actor=agent)
    except QueueItemNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/{item_id}/assign", response_model=QueueItemResponse)
async def assign_queue_item(
    item_id: uuid.UUID, db: DBSession, agent: CurrentAgent
) -> QueueItemResponse:
    """Assign the queue item to the requesting agent."""
    service = QueueService(db)
    try:
        return await service.assign_to_agent(item_id=item_id, agent_id=agent["sub"])
    except QueueItemNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
