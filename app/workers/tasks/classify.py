"""classify_call — load transcript, call Claude, create classification + queue item."""
import uuid

import structlog
from arq import ArqRedis
from sqlalchemy import select

from app.config import get_settings
from app.db.models.transcript import Transcript
from app.db.session import AsyncSessionLocal
from app.domain.classification.service import ClassificationService
from app.utils.encryption import PHIEncryptor

log = structlog.get_logger(__name__)
settings = get_settings()


async def classify_call(ctx: dict, call_id: str) -> None:
    """ARQ task: decrypt transcript, classify via Claude, create queue item."""
    call_uuid = uuid.UUID(call_id)
    encryptor = PHIEncryptor()

    async with AsyncSessionLocal() as db:
        stmt = select(Transcript).where(Transcript.call_id == call_uuid)
        result = await db.execute(stmt)
        transcript_row = result.scalar_one_or_none()

        if transcript_row is None or not transcript_row.raw_transcript_encrypted:
            log.error("classify.no_transcript", call_id=call_id)
            return

        plaintext = encryptor.decrypt(transcript_row.raw_transcript_encrypted)
        if not plaintext:
            log.error("classify.decrypt_failed", call_id=call_id)
            return

        service = ClassificationService(db)
        await service.classify_call(call_id=call_uuid, transcript=plaintext)
        await db.commit()

    log.info("classify.complete", call_id=call_id)


async def enqueue_classify(call_id: uuid.UUID) -> None:
    from arq.connections import RedisSettings, create_pool
    redis: ArqRedis = await create_pool(RedisSettings.from_dsn(str(settings.redis_url)))
    await redis.enqueue_job("classify_call", str(call_id))
    await redis.aclose()
