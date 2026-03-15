"""Async callback from the transcription provider when a job completes."""
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.dependencies import DBSession
from app.domain.calls.service import CallService

router = APIRouter(prefix="/webhooks/transcription", tags=["webhooks"])


class TranscriptionCompletePayload(BaseModel):
    job_id: str
    transcript: str
    provider: str = "deepgram"


@router.post("/complete", status_code=status.HTTP_204_NO_CONTENT)
async def transcription_complete(
    payload: TranscriptionCompletePayload,
    db: DBSession,
    x_deepgram_signature: str | None = Header(default=None),
) -> None:
    """Receives completed transcription from provider.
    Stores transcript and enqueues classification worker task."""
    # In production: verify the provider-specific HMAC signature here.
    # Omitted for initial scaffold — add before public deployment.
    service = CallService(db)
    await service.handle_transcription_complete(
        provider_job_id=payload.job_id,
        transcript=payload.transcript,
        provider=payload.provider,
    )
