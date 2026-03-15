"""Inbound webhooks from the telephony provider (Twilio).

Twilio sends form-encoded POST data and expects TwiML XML responses.
Signature failures return 403 — never 401 — to avoid leaking auth scheme info.
"""
from fastapi import APIRouter, Form, Header, HTTPException, Request, status
from fastapi.responses import Response

from app.config import get_settings
from app.dependencies import DBSession
from app.domain.calls.service import CallService
from app.integrations.telephony.twilio import TwilioProvider

router = APIRouter(prefix="/webhooks/telephony", tags=["webhooks"])
settings = get_settings()

TWIML_GREET_AND_RECORD = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">
        Thank you for calling. Please leave a message after the tone and we will follow up shortly.
    </Say>
    <Record maxLength="300" playBeep="true" transcribe="false" />
    <Say>Thank you. Goodbye.</Say>
    <Hangup/>
</Response>"""

TWIML_GOODBYE = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling. Goodbye.</Say>
    <Hangup/>
</Response>"""


def _twiml(xml: str) -> Response:
    return Response(content=xml, media_type="application/xml")


async def _verify_twilio(request: Request, signature: str | None, params: dict) -> None:
    """Verify Twilio signature. Skipped in non-production to simplify local/staging testing."""
    if not settings.is_production:
        return
    if not signature:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing signature")
    provider = TwilioProvider()
    if not provider.verify_signature(url=settings.twilio_webhook_url, params=params, signature=signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")


@router.post("/call-started")
async def call_started(
    db: DBSession,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
) -> Response:
    """Fires when a new inbound call is established. Returns TwiML to greet and record."""
    service = CallService(db)
    await service.handle_call_started(external_call_id=CallSid, caller_phone=From)
    return _twiml(TWIML_GREET_AND_RECORD)


@router.post("/call-ended")
async def call_ended(
    db: DBSession,
    CallSid: str = Form(...),
    CallDuration: str | None = Form(default=None),
    RecordingUrl: str | None = Form(default=None),
) -> Response:
    """Fires when a call ends. Triggers transcription pipeline."""
    service = CallService(db)
    await service.handle_call_ended(
        external_call_id=CallSid,
        duration_seconds=int(CallDuration) if CallDuration else None,
        recording_url=RecordingUrl,
    )
    return _twiml(TWIML_GOODBYE)


@router.post("/transfer")
async def call_transferred(
    db: DBSession,
    CallSid: str = Form(...),
    AgentId: str | None = Form(default=None),
    AgentName: str | None = Form(default=None),
) -> Response:
    """Fires when the AI transfers a call to a human agent."""
    service = CallService(db)
    await service.handle_call_transferred(
        external_call_id=CallSid,
        agent_external_id=AgentId,
        agent_name=AgentName,
    )
    return _twiml(TWIML_GOODBYE)
