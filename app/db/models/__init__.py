# Import all models here so Alembic autogenerate can discover them.
from app.db.models.agent import Agent
from app.db.models.audit_log import AuditLog
from app.db.models.call import Call
from app.db.models.classification import Classification
from app.db.models.crm_sync_log import CRMSyncLog
from app.db.models.queue_item import QueueItem
from app.db.models.transcript import Transcript

__all__ = [
    "Agent",
    "AuditLog",
    "Call",
    "Classification",
    "CRMSyncLog",
    "QueueItem",
    "Transcript",
]
