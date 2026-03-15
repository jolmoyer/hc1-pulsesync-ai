import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.call import Call
from app.db.models.classification import Classification
from app.db.models.crm_sync_log import CRMSyncLog, SyncStatus
from app.db.models.queue_item import QueueItem, QueueStatus
from app.domain.calls.exceptions import CallNotFoundError
from app.schemas.sync import SyncLogResponse, SyncStatusResponse, SyncTriggerResponse
from app.utils.encryption import PHIEncryptor

log = structlog.get_logger(__name__)


class SyncService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._encryptor = PHIEncryptor()

    async def enqueue_sync(
        self, call_id: uuid.UUID, initiated_by: str
    ) -> SyncTriggerResponse:
        call = await self._get_call(call_id)
        classification = await self._get_classification(call_id)
        if classification is None:
            raise ValueError("Call has not been classified yet. Cannot sync to CRM.")

        # Create a PENDING sync log entry upfront for idempotency tracking
        sync_log = CRMSyncLog(
            call_id=call_id,
            initiated_by_id=uuid.UUID(initiated_by),
            status=SyncStatus.PENDING,
            attempted_at=datetime.now(timezone.utc),
        )
        self._db.add(sync_log)
        await self._db.flush()

        # Enqueue background worker
        from app.workers.tasks.crm_push import enqueue_crm_push
        job_id = await enqueue_crm_push(
            call_id=call_id, sync_log_id=sync_log.id, initiated_by=initiated_by
        )

        log.info("sync.enqueued", call_id=str(call_id), job_id=str(job_id))
        return SyncTriggerResponse(
            job_id=str(job_id),
            call_id=call_id,
            status=SyncStatus.PENDING,
            message="CRM sync job enqueued successfully.",
        )

    async def get_latest_status(self, call_id: uuid.UUID) -> SyncStatusResponse | None:
        stmt = (
            select(CRMSyncLog)
            .where(CRMSyncLog.call_id == call_id)
            .order_by(CRMSyncLog.attempted_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        log_row = result.scalar_one_or_none()
        if log_row is None:
            return None
        return SyncStatusResponse(
            call_id=log_row.call_id,
            status=log_row.status,
            crm_record_id=log_row.crm_record_id,
            crm_record_type=log_row.crm_record_type,
            error_message=log_row.error_message,
            attempted_at=log_row.attempted_at,
            completed_at=log_row.completed_at,
        )

    async def get_history(self, call_id: uuid.UUID) -> list[SyncLogResponse]:
        stmt = (
            select(CRMSyncLog)
            .where(CRMSyncLog.call_id == call_id)
            .order_by(CRMSyncLog.attempted_at.desc())
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return [SyncLogResponse.model_validate(r) for r in rows]

    async def _get_call(self, call_id: uuid.UUID) -> Call:
        stmt = select(Call).where(Call.id == call_id)
        result = await self._db.execute(stmt)
        call = result.scalar_one_or_none()
        if call is None:
            raise CallNotFoundError(call_id)
        return call

    async def _get_classification(self, call_id: uuid.UUID) -> Classification | None:
        stmt = select(Classification).where(Classification.call_id == call_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()
