import uuid
from datetime import datetime

from pydantic import BaseModel


class SyncTriggerResponse(BaseModel):
    job_id: str
    call_id: uuid.UUID
    status: str
    message: str


class SyncStatusResponse(BaseModel):
    call_id: uuid.UUID
    status: str
    crm_record_id: str | None
    crm_record_type: str | None
    error_message: str | None
    attempted_at: datetime
    completed_at: datetime | None


class SyncLogResponse(BaseModel):
    id: uuid.UUID
    call_id: uuid.UUID
    initiated_by_id: uuid.UUID | None
    status: str
    crm_record_id: str | None
    crm_record_type: str | None
    error_message: str | None
    attempted_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
