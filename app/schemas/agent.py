import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    role: str = Field(default="reviewer", pattern="^(reviewer|admin)$")
    external_id: str | None = None


class AgentCreate(AgentBase):
    password: str = Field(..., min_length=12)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    role: str | None = Field(default=None, pattern="^(reviewer|admin)$")
    external_id: str | None = None
    is_active: bool | None = None


class AgentResponse(AgentBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    total: int
    page: int
    page_size: int
