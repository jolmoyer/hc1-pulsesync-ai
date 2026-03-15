import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.call import Call


class Transcript(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Isolated PHI table. raw_transcript_encrypted contains AES-256
    ciphertext of the full call transcript."""

    __tablename__ = "transcripts"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    # PHI — encrypted at rest
    raw_transcript_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transcribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    call: Mapped["Call"] = relationship("Call", back_populates="transcript")

    def __repr__(self) -> str:
        return f"<Transcript id={self.id} call_id={self.call_id} provider={self.provider}>"
