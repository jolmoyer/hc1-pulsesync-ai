"""Async callback from the transcription provider when a job completes."""
from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from app.dependencies import DBSession
from app.domain.calls.service import CallService

router = APIRouter(prefix="/webhooks/transcription", tags=["webhooks"])


@router.post("/complete", status_code=status.HTTP_204_NO_CONTENT)
async def transcription_complete(
    request: Request,
    db: DBSession,
    x_deepgram_signature: str | None = Header(default=None),
) -> None:
    """Receives completed transcription callback from Deepgram.
    Parses Deepgram's native response format, stores transcript, enqueues classification."""
    data = await request.json()

    # Extract job_id from Deepgram's metadata
    job_id: str = data.get("metadata", {}).get("request_id", "")

    # Extract transcript text from Deepgram's results structure
    transcript_text = ""
    try:
        channels = data.get("results", {}).get("channels", [])
        if channels:
            alternatives = channels[0].get("alternatives", [])
            if alternatives:
                transcript_text = alternatives[0].get("transcript", "")
    except (KeyError, IndexError):
        transcript_text = ""

    if not job_id:
        return

    service = CallService(db)
    await service.handle_transcription_complete(
        provider_job_id=job_id,
        transcript=transcript_text,
        provider="deepgram",
    )
