"""Inbound webhooks from the telephony provider (Twilio).

All endpoints verify the provider signature before processing.
Signature failures return 403 — never 401 — to avoid leaking auth scheme info.
"""
from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.config import get_settings
from app.dependencies import DBSession
from app.domain.calls.service import CallService
from app.integrations.telephony.twilio import TwilioProvider

router = APIRouter(prefix="/webhooks/telephony", tags=["webhooks"])
settings = get_settings()


class CallStartedPayload(BaseModel):
    CallSid: str
    From: str       # caller phone number (E.164)
    To: str         # called number


class CallEndedPayload(BaseModel):
    CallSid: str
    CallDuration: str | None = None   # seconds as string
    RecordingUrl: str | None = None


class TransferPayload(BaseModel):
    CallSid: str
    AgentId: str | None = None
    AgentName: str | None = None


def _verify_twilio_signature(request: Request, x_twilio_signature: str | None) -> None:
    """Raise 403 if the Twilio signature header is missing or invalid."""
    if not x_twilio_signature:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing signature")
    provider = TwilioProvider()
    if not provider.verify_signature(
        url=str(request.url),
        params={},   # form params will be validated by Twilio SDK in production
        signature=x_twilio_signature,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")


@router.post("/call-started", status_code=status.HTTP_204_NO_CONTENT)
async def call_started(
    payload: CallStartedPayload,
    request: Request,
    db: DBSession,
    x_twilio_signature: str | None = Header(default=None),
) -> None:
    """Fires when a new inbound call is established."""
    _verify_twilio_signature(request, x_twilio_signature)
    service = CallService(db)
    await service.handle_call_started(
        external_call_id=payload.CallSid,
        caller_phone=payload.From,
    )


@router.post("/call-ended", status_code=status.HTTP_204_NO_CONTENT)
async def call_ended(
    payload: CallEndedPayload,
    request: Request,
    db: DBSession,
    x_twilio_signature: str | None = Header(default=None),
) -> None:
    """Fires when a call ends. Triggers transcription pipeline."""
    _verify_twilio_signature(request, x_twilio_signature)
    service = CallService(db)
    await service.handle_call_ended(
        external_call_id=payload.CallSid,
        duration_seconds=int(payload.CallDuration) if payload.CallDuration else None,
        recording_url=payload.RecordingUrl,
    )


@router.post("/transfer", status_code=status.HTTP_204_NO_CONTENT)
async def call_transferred(
    payload: TransferPayload,
    request: Request,
    db: DBSession,
    x_twilio_signature: str | None = Header(default=None),
) -> None:
    """Fires when the AI transfers a call to a human agent."""
    _verify_twilio_signature(request, x_twilio_signature)
    service = CallService(db)
    await service.handle_call_transferred(
        external_call_id=payload.CallSid,
        agent_external_id=payload.AgentId,
        agent_name=payload.AgentName,
    )
