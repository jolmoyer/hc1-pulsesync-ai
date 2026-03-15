"""Maps a call record + classification to a CRM Case or Task payload."""
from app.db.models.call import Call
from app.db.models.classification import Classification, ClassificationType


def build_crm_payload(call: Call, classification: Classification, caller_name: str | None, caller_phone: str | None) -> dict:
    """Return the payload dict to send to the CRM API."""
    base = {
        "source": "PulseSync AI",
        "caller_phone": caller_phone,
        "caller_name": caller_name,
        "summary": classification.ai_summary or "",
        "notes": classification.reviewer_notes or "",
        "call_duration_seconds": call.duration_seconds,
        "was_transferred": call.was_transferred,
        "call_started_at": call.started_at.isoformat() if call.started_at else None,
        "call_ended_at": call.ended_at.isoformat() if call.ended_at else None,
    }

    if classification.classification == ClassificationType.CASE:
        return {**base, "type": "CASE", "priority": "NORMAL", "status": "OPEN"}
    else:
        return {**base, "type": "TASK", "status": "PENDING"}
