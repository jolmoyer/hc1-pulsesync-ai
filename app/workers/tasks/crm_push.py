"""push_to_crm — execute the CRM sync for a single call."""
import uuid
from datetime import datetime, timezone

import structlog
from arq import ArqRedis
from sqlalchemy import select

from app.config import get_settings
from app.db.models.call import Call
from app.db.models.classification import Classification, ClassificationType
from app.db.models.crm_sync_log import CRMSyncLog, SyncStatus
from app.db.models.queue_item import QueueItem, QueueStatus
from app.db.session import AsyncSessionLocal
from app.domain.sync.mapper import build_crm_payload
from app.integrations.crm.hc1_crm import HC1CRMClient
from app.utils.encryption import PHIEncryptor

log = structlog.get_logger(__name__)
settings = get_settings()


async def push_to_crm(ctx: dict, call_id: str, sync_log_id: str, initiated_by: str) -> None:
    """ARQ task: build payload, call CRM API, update sync log and queue item."""
    call_uuid = uuid.UUID(call_id)
    sync_log_uuid = uuid.UUID(sync_log_id)
    encryptor = PHIEncryptor()
    crm = HC1CRMClient()

    async with AsyncSessionLocal() as db:
        call = (await db.execute(select(Call).where(Call.id == call_uuid))).scalar_one_or_none()
        classification = (
            await db.execute(select(Classification).where(Classification.call_id == call_uuid))
        ).scalar_one_or_none()
        sync_log = (
            await db.execute(select(CRMSyncLog).where(CRMSyncLog.id == sync_log_uuid))
        ).scalar_one_or_none()

        if not call or not classification or not sync_log:
            log.error("crm_push.missing_data", call_id=call_id)
            return

        caller_phone = encryptor.decrypt(call.caller_phone_encrypted) if call.caller_phone_encrypted else None
        caller_name = encryptor.decrypt(call.caller_name_encrypted) if call.caller_name_encrypted else None
        payload = build_crm_payload(call, classification, caller_name, caller_phone)

        try:
            if classification.classification == ClassificationType.CASE:
                record = await crm.create_case(payload)
            else:
                record = await crm.create_task(payload)

            sync_log.status = SyncStatus.SUCCESS
            sync_log.crm_record_id = record.record_id
            sync_log.crm_record_type = record.record_type
            sync_log.request_payload = payload
            sync_log.completed_at = datetime.now(timezone.utc)

            # Advance queue item to SYNCED
            queue_item = (
                await db.execute(select(QueueItem).where(QueueItem.call_id == call_uuid))
            ).scalar_one_or_none()
            if queue_item:
                queue_item.status = QueueStatus.SYNCED

            log.info("crm_push.success", call_id=call_id, record_id=record.record_id)

        except Exception as exc:
            sync_log.status = SyncStatus.FAILED
            sync_log.error_message = str(exc)
            sync_log.completed_at = datetime.now(timezone.utc)
            log.error("crm_push.failed", call_id=call_id, error=str(exc))

        await db.commit()


async def enqueue_crm_push(
    call_id: uuid.UUID, sync_log_id: uuid.UUID, initiated_by: str
) -> str:
    from arq.connections import RedisSettings, create_pool
    redis: ArqRedis = await create_pool(RedisSettings.from_dsn(str(settings.redis_url)))
    job = await redis.enqueue_job("push_to_crm", str(call_id), str(sync_log_id), initiated_by)
    await redis.aclose()
    return job.job_id if job else str(sync_log_id)
