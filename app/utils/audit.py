"""AuditService — HIPAA-compliant append-only access audit logging."""
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog

log = structlog.get_logger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log(
        self,
        actor: dict | None,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Write an audit log entry. Fire-and-forget — never raises."""
        try:
            actor_id = uuid.UUID(actor["sub"]) if actor and "sub" in actor else None
            actor_type = "agent" if actor_id else "system"
            entry = AuditLog(
                actor_id=actor_id,
                actor_type=actor_type,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._db.add(entry)
            await self._db.flush()
        except Exception as exc:
            # Audit failures must never break the primary request path.
            log.error("audit.write_failed", error=str(exc), action=action)
