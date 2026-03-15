from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.call import Call
    from app.db.models.classification import Classification
    from app.db.models.crm_sync_log import CRMSyncLog
    from app.db.models.queue_item import QueueItem


class Agent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Human customer service agent who reviews queue items and syncs to CRM."""

    __tablename__ = "agents"

    external_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="reviewer"
    )  # reviewer | admin
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    transferred_calls: Mapped[list["Call"]] = relationship(
        "Call", back_populates="transferred_to_agent", foreign_keys="Call.transferred_to_agent_id"
    )
    reviewed_classifications: Mapped[list["Classification"]] = relationship(
        "Classification", back_populates="reviewed_by_agent"
    )
    queue_assignments: Mapped[list["QueueItem"]] = relationship(
        "QueueItem", back_populates="assigned_agent"
    )
    crm_syncs: Mapped[list["CRMSyncLog"]] = relationship(
        "CRMSyncLog", back_populates="initiated_by_agent"
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} email={self.email} role={self.role}>"
