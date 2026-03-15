import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.call import CallResponse


class QueueItemResponse(BaseModel):
    id: uuid.UUID
    call_id: uuid.UUID
    status: str
    assigned_to: uuid.UUID | None
    assigned_at: datetime | None
    created_at: datetime
    updated_at: datetime
    call: CallResponse | None = None

    model_config = {"from_attributes": True}


class QueueItemUpdate(BaseModel):
    status: str | None = None
    reviewer_notes: str | None = None


class QueueListResponse(BaseModel):
    items: list[QueueItemResponse]
    total: int
    page: int
    page_size: int
