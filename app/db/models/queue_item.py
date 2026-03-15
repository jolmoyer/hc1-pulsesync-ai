import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.agent import Agent
    from app.db.models.call import Call


class QueueStatus:
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    SYNCED = "SYNCED"
    DISMISSED = "DISMISSED"

    VALID_TRANSITIONS: dict[str, list[str]] = {
        PENDING_REVIEW: [IN_REVIEW, DISMISSED],
        IN_REVIEW: [APPROVED, PENDING_REVIEW, DISMISSED],
        APPROVED: [SYNCED, IN_REVIEW],
        SYNCED: [],         # terminal — cannot re-sync without explicit admin action
        DISMISSED: [],      # terminal
    }

    @classmethod
    def can_transition(cls, current: str, target: str) -> bool:
        return target in cls.VALID_TRANSITIONS.get(current, [])


class QueueItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Review queue entry for a completed, classified call."""

    __tablename__ = "queue_items"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=QueueStatus.PENDING_REVIEW
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    call: Mapped["Call"] = relationship("Call", back_populates="queue_item")
    assigned_agent: Mapped["Agent | None"] = relationship(
        "Agent", back_populates="queue_assignments", foreign_keys=[assigned_to]
    )

    def __repr__(self) -> str:
        return f"<QueueItem id={self.id} call_id={self.call_id} status={self.status}>"
