import uuid

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentAgent, DBSession
from app.domain.calls.exceptions import CallNotFoundError
from app.domain.sync.service import SyncService
from app.schemas.sync import SyncLogResponse, SyncStatusResponse, SyncTriggerResponse

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/{call_id}", response_model=SyncTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(
    call_id: uuid.UUID, db: DBSession, agent: CurrentAgent
) -> SyncTriggerResponse:
    """Enqueue a CRM sync job for the specified call. Returns immediately."""
    service = SyncService(db)
    try:
        return await service.enqueue_sync(call_id=call_id, initiated_by=agent["sub"])
    except CallNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{call_id}/status", response_model=SyncStatusResponse)
async def get_sync_status(
    call_id: uuid.UUID, db: DBSession, _: CurrentAgent
) -> SyncStatusResponse:
    """Return the latest sync attempt status for a call."""
    service = SyncService(db)
    result = await service.get_latest_status(call_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sync record found")
    return result


@router.get("/{call_id}/history", response_model=list[SyncLogResponse])
async def get_sync_history(
    call_id: uuid.UUID, db: DBSession, _: CurrentAgent
) -> list[SyncLogResponse]:
    """Return full sync attempt history for a call."""
    service = SyncService(db)
    return await service.get_history(call_id)
