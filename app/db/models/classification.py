import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.agent import Agent
    from app.db.models.call import Call


class ClassificationType:
    CASE = "CASE"
    TASK = "TASK"


class Classification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AI-generated classification and summary for a completed call."""

    __tablename__ = "classifications"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    classification: Mapped[str] = mapped_column(String(50), nullable=False)  # CASE | TASK
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    call: Mapped["Call"] = relationship("Call", back_populates="classification")
    reviewed_by_agent: Mapped["Agent | None"] = relationship(
        "Agent", back_populates="reviewed_classifications", foreign_keys=[reviewed_by_id]
    )

    def __repr__(self) -> str:
        return (
            f"<Classification id={self.id} call_id={self.call_id} "
            f"type={self.classification} confidence={self.confidence}>"
        )
