"""transcribe_call — download audio and submit to transcription provider."""
import uuid
from datetime import datetime, timezone

import structlog
from arq import ArqRedis

from app.config import get_settings
from app.db.models.transcript import Transcript
from app.db.session import AsyncSessionLocal
from app.integrations.transcription.deepgram import DeepgramProvider

log = structlog.get_logger(__name__)
settings = get_settings()


async def transcribe_call(ctx: dict, call_id: str, recording_url: str | None) -> None:
    """ARQ task: submit recording to transcription provider and store job ID."""
    call_uuid = uuid.UUID(call_id)

    if not recording_url:
        log.warning("transcribe.no_recording_url", call_id=call_id)
        return

    provider = DeepgramProvider()
    job_id = await provider.submit_job(
        recording_url=recording_url,
        callback_url=settings.transcription_callback_url,
    )

    async with AsyncSessionLocal() as db:
        transcript = Transcript(
            call_id=call_uuid,
            provider="deepgram",
            provider_job_id=job_id,
        )
        db.add(transcript)
        await db.commit()

    log.info("transcribe.job_submitted", call_id=call_id, job_id=job_id)


async def enqueue_transcribe(call_id: uuid.UUID, recording_url: str | None) -> None:
    """Helper called by CallService to enqueue this task."""
    from arq.connections import RedisSettings, create_pool
    redis: ArqRedis = await create_pool(RedisSettings.from_dsn(str(settings.redis_url)))
    await redis.enqueue_job("transcribe_call", str(call_id), recording_url)
    await redis.aclose()
