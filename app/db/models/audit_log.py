import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.agent import Agent
    from app.db.models.call import Call


class AuditAction:
    """Enumeration of auditable actions for HIPAA compliance."""

    READ_TRANSCRIPT = "READ_TRANSCRIPT"
    READ_CALL = "READ_CALL"
    UPDATE_CALL = "UPDATE_CALL"
    SYNC_CRM = "SYNC_CRM"
    REVIEW_QUEUE_ITEM = "REVIEW_QUEUE_ITEM"
    DISMISS_QUEUE_ITEM = "DISMISS_QUEUE_ITEM"
    AGENT_LOGIN = "AGENT_LOGIN"
    AGENT_LOGOUT = "AGENT_LOGOUT"
    CLASSIFY_CALL = "CLASSIFY_CALL"


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only HIPAA audit trail. Never deleted or updated."""

    __tablename__ = "audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)  # agent | system | worker
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    actor: Mapped["Agent | None"] = relationship("Agent", foreign_keys=[actor_id])
    call: Mapped["Call | None"] = relationship(
        "Call",
        foreign_keys=[resource_id],
        primaryjoin="and_(AuditLog.resource_id == Call.id, AuditLog.resource_type == 'call')",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} actor={self.actor_id} "
            f"action={self.action} resource={self.resource_type}:{self.resource_id}>"
        )
