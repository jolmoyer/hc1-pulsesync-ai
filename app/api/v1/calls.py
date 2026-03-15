import uuid

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.dependencies import CurrentAgent, DBSession
from app.domain.calls.exceptions import CallNotFoundError
from app.domain.calls.service import CallService
from app.schemas.call import CallListResponse, CallResponse, CallUpdate, TranscriptResponse

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("", response_model=CallListResponse)
async def list_calls(
    db: DBSession,
    _: CurrentAgent,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
) -> CallListResponse:
    """List calls with optional status filter, paginated."""
    service = CallService(db)
    return await service.list_calls(page=page, page_size=page_size, status_filter=status)


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(call_id: uuid.UUID, db: DBSession, agent: CurrentAgent) -> CallResponse:
    """Get a single call record. PHI is decrypted for authorised agents."""
    service = CallService(db)
    try:
        return await service.get_call(call_id=call_id, actor=agent)
    except CallNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")


@router.get("/{call_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    call_id: uuid.UUID, request: Request, db: DBSession, agent: CurrentAgent
) -> TranscriptResponse:
    """Retrieve the call transcript. Access is audit-logged per HIPAA requirements."""
    service = CallService(db)
    try:
        return await service.get_transcript(
            call_id=call_id,
            actor=agent,
            ip_address=request.client.host if request.client else None,
        )
    except CallNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")


@router.patch("/{call_id}", response_model=CallResponse)
async def update_call(
    call_id: uuid.UUID, payload: CallUpdate, db: DBSession, agent: CurrentAgent
) -> CallResponse:
    """Update editable fields on a call before CRM sync."""
    service = CallService(db)
    try:
        return await service.update_call(call_id=call_id, payload=payload, actor=agent)
    except CallNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
