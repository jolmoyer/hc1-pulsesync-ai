"""ARQ worker entry point.

Run with:
    python -m app.workers.worker
"""
from arq.connections import RedisSettings

from app.config import get_settings
from app.workers.tasks.classify import classify_call
from app.workers.tasks.crm_push import push_to_crm
from app.workers.tasks.transcribe import transcribe_call

settings = get_settings()


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [transcribe_call, classify_call, push_to_crm]

    redis_settings = RedisSettings.from_dsn(str(settings.redis_url))

    # Retry settings
    max_tries = 3
    job_timeout = 300     # 5 minutes per job
    keep_result = 3600    # keep job result in Redis for 1 hour

    # Health check
    health_check_interval = 30
    health_check_key = "pulsesync:worker:health"

    on_startup = None
    on_shutdown = None


if __name__ == "__main__":
    import asyncio
    from arq import run_worker
    asyncio.run(run_worker(WorkerSettings))  # type: ignore[arg-type]
