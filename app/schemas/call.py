import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CallResponse(BaseModel):
    id: uuid.UUID
    external_call_id: str
    caller_phone: str | None  # decrypted on read
    caller_name: str | None   # decrypted on read
    status: str
    duration_seconds: int | None
    was_transferred: bool
    transferred_to_agent_id: uuid.UUID | None
    transfer_timestamp: datetime | None
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CallUpdate(BaseModel):
    caller_name: str | None = Field(default=None, max_length=255)


class TranscriptResponse(BaseModel):
    id: uuid.UUID
    call_id: uuid.UUID
    transcript: str | None   # decrypted on read
    provider: str | None
    transcribed_at: datetime | None

    model_config = {"from_attributes": True}


class CallListResponse(BaseModel):
    items: list[CallResponse]
    total: int
    page: int
    page_size: int
