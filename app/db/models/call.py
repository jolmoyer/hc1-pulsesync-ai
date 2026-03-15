import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.agent import Agent
    from app.db.models.audit_log import AuditLog
    from app.db.models.classification import Classification
    from app.db.models.crm_sync_log import CRMSyncLog
    from app.db.models.queue_item import QueueItem
    from app.db.models.transcript import Transcript


class CallStatus:
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Call(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Core call record. PHI columns (caller_phone, caller_name) are
    stored as application-level encrypted ciphertext."""

    __tablename__ = "calls"

    external_call_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # PHI — encrypted at rest via PHIEncryptor
    caller_phone_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    caller_name_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=CallStatus.ACTIVE
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    was_transferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    transferred_to_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    transfer_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    transferred_to_agent: Mapped["Agent | None"] = relationship(
        "Agent",
        back_populates="transferred_calls",
        foreign_keys=[transferred_to_agent_id],
    )
    transcript: Mapped["Transcript | None"] = relationship(
        "Transcript", back_populates="call", uselist=False, cascade="all, delete-orphan"
    )
    classification: Mapped["Classification | None"] = relationship(
        "Classification", back_populates="call", uselist=False, cascade="all, delete-orphan"
    )
    queue_item: Mapped["QueueItem | None"] = relationship(
        "QueueItem", back_populates="call", uselist=False, cascade="all, delete-orphan"
    )
    crm_sync_logs: Mapped[list["CRMSyncLog"]] = relationship(
        "CRMSyncLog", back_populates="call", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="call",
        foreign_keys="AuditLog.resource_id",
        primaryjoin="and_(AuditLog.resource_id == Call.id, AuditLog.resource_type == 'call')",
    )

    def __repr__(self) -> str:
        return f"<Call id={self.id} external_id={self.external_call_id} status={self.status}>"
