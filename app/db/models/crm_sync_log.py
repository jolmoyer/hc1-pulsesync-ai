import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.agent import Agent
    from app.db.models.call import Call


class SyncStatus:
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class CRMSyncLog(UUIDPrimaryKeyMixin, Base):
    """Immutable audit record of every CRM push attempt."""

    __tablename__ = "crm_sync_logs"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False
    )
    initiated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=SyncStatus.PENDING)
    crm_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crm_record_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    request_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    call: Mapped["Call"] = relationship("Call", back_populates="crm_sync_logs")
    initiated_by_agent: Mapped["Agent | None"] = relationship(
        "Agent", back_populates="crm_syncs", foreign_keys=[initiated_by_id]
    )

    def __repr__(self) -> str:
        return (
            f"<CRMSyncLog id={self.id} call_id={self.call_id} status={self.status}>"
        )
