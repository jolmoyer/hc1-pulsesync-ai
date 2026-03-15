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
    """Raise 403 if the Twilio signature is missing or invalid.

    We reconstruct the URL from settings because Railway sits behind a reverse
    proxy and request.url reflects the internal address, not the public one
    that Twilio signed against.
    """
    if not signature:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing signature")
    # Build the canonical URL Twilio signed: base webhook URL + the specific path suffix
    path_suffix = request.url.path.replace("/webhooks/telephony", "", 1)
    canonical_url = settings.twilio_webhook_url.rstrip("/") + path_suffix
    provider = TwilioProvider()
    if not provider.verify_signature(url=canonical_url, params=params, signature=signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")


@router.post("/call-started")
async def call_started(
    request: Request,
    db: DBSession,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    x_twilio_signature: str | None = Header(default=None),
) -> Response:
    """Fires when a new inbound call is established. Returns TwiML to greet and record."""
    params = {"CallSid": CallSid, "From": From, "To": To}
    await _verify_twilio(request, x_twilio_signature, params)
    service = CallService(db)
    await service.handle_call_started(external_call_id=CallSid, caller_phone=From)
    return _twiml(TWIML_GREET_AND_RECORD)


@router.post("/call-ended")
async def call_ended(
    request: Request,
    db: DBSession,
    CallSid: str = Form(...),
    CallDuration: str | None = Form(default=None),
    RecordingUrl: str | None = Form(default=None),
    x_twilio_signature: str | None = Header(default=None),
) -> Response:
    """Fires when a call ends. Triggers transcription pipeline."""
    params = {"CallSid": CallSid}
    if CallDuration:
        params["CallDuration"] = CallDuration
    if RecordingUrl:
        params["RecordingUrl"] = RecordingUrl
    await _verify_twilio(request, x_twilio_signature, params)
    service = CallService(db)
    await service.handle_call_ended(
        external_call_id=CallSid,
        duration_seconds=int(CallDuration) if CallDuration else None,
        recording_url=RecordingUrl,
    )
    return _twiml(TWIML_GOODBYE)


@router.post("/transfer")
async def call_transferred(
    request: Request,
    db: DBSession,
    CallSid: str = Form(...),
    AgentId: str | None = Form(default=None),
    AgentName: str | None = Form(default=None),
    x_twilio_signature: str | None = Header(default=None),
) -> Response:
    """Fires when the AI transfers a call to a human agent."""
    params = {"CallSid": CallSid}
    await _verify_twilio(request, x_twilio_signature, params)
    service = CallService(db)
    await service.handle_call_transferred(
        external_call_id=CallSid,
        agent_external_id=AgentId,
        agent_name=AgentName,
    )
    return _twiml(TWIML_GOODBYE)
