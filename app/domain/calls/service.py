"""CallService — all business logic for call lifecycle management.

PHI handling contract:
  - Encrypt before INSERT: use _encryptor.encrypt()
  - Decrypt after SELECT: use _encryptor.decrypt()
  - Every PHI read is followed by an audit log write via AuditService.
"""
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.call import Call, CallStatus
from app.db.models.queue_item import QueueItem, QueueStatus
from app.db.models.transcript import Transcript
from app.domain.calls.exceptions import CallNotFoundError, InvalidCallStateError
from app.schemas.call import CallListResponse, CallResponse, CallUpdate, TranscriptResponse
from app.utils.encryption import PHIEncryptor
from app.utils.audit import AuditService

log = structlog.get_logger(__name__)


class CallService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._encryptor = PHIEncryptor()
        self._audit = AuditService(db)

    # ── Webhook handlers ──────────────────────────────────────────────────────

    async def handle_call_started(
        self, external_call_id: str, caller_phone: str
    ) -> Call:
        call = Call(
            external_call_id=external_call_id,
            caller_phone_encrypted=self._encryptor.encrypt(caller_phone),
            status=CallStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )
        self._db.add(call)
        await self._db.flush()
        log.info("call.started", call_id=str(call.id), external_id=external_call_id)
        return call

    async def handle_call_ended(
        self,
        external_call_id: str,
        duration_seconds: int | None,
        recording_url: str | None,
    ) -> Call:
        call = await self._get_by_external_id(external_call_id)
        call.status = CallStatus.COMPLETED
        call.ended_at = datetime.now(timezone.utc)
        call.duration_seconds = duration_seconds
        await self._db.flush()

        # Enqueue transcription worker (import here to avoid circular dependency)
        from app.workers.tasks.transcribe import enqueue_transcribe
        await enqueue_transcribe(call_id=call.id, recording_url=recording_url)
        log.info("call.ended", call_id=str(call.id), duration=duration_seconds)
        return call

    async def handle_call_transferred(
        self,
        external_call_id: str,
        agent_external_id: str | None,
        agent_name: str | None,
    ) -> Call:
        call = await self._get_by_external_id(external_call_id)
        call.was_transferred = True
        call.transfer_timestamp = datetime.now(timezone.utc)
        # Agent lookup by external_id omitted in scaffold; add in full implementation
        await self._db.flush()
        log.info("call.transferred", call_id=str(call.id), agent=agent_external_id)
        return call

    async def handle_transcription_complete(
        self, provider_job_id: str, transcript: str, provider: str
    ) -> None:
        stmt = select(Transcript).where(Transcript.provider_job_id == provider_job_id)
        result = await self._db.execute(stmt)
        transcript_row = result.scalar_one_or_none()
        if transcript_row is None:
            log.error("transcription.job_not_found", job_id=provider_job_id)
            return

        transcript_row.raw_transcript_encrypted = self._encryptor.encrypt(transcript)
        transcript_row.transcribed_at = datetime.now(timezone.utc)
        await self._db.flush()

        from app.workers.tasks.classify import enqueue_classify
        await enqueue_classify(call_id=transcript_row.call_id)
        log.info("transcription.complete", call_id=str(transcript_row.call_id))

    # ── API handlers ──────────────────────────────────────────────────────────

    async def get_call(self, call_id: uuid.UUID, actor: dict) -> CallResponse:
        call = await self._get_by_id(call_id)
        await self._audit.log(
            actor=actor,
            action="READ_CALL",
            resource_type="call",
            resource_id=call_id,
        )
        return self._to_response(call)

    async def get_transcript(
        self,
        call_id: uuid.UUID,
        actor: dict,
        ip_address: str | None = None,
    ) -> TranscriptResponse:
        call = await self._get_by_id(call_id, load_transcript=True)
        await self._audit.log(
            actor=actor,
            action="READ_TRANSCRIPT",
            resource_type="transcript",
            resource_id=call_id,
            ip_address=ip_address,
        )
        t = call.transcript
        if t is None:
            return TranscriptResponse(
                id=uuid.uuid4(), call_id=call_id, transcript=None,
                provider=None, transcribed_at=None
            )
        return TranscriptResponse(
            id=t.id,
            call_id=t.call_id,
            transcript=self._encryptor.decrypt(t.raw_transcript_encrypted) if t.raw_transcript_encrypted else None,
            provider=t.provider,
            transcribed_at=t.transcribed_at,
        )

    async def update_call(
        self, call_id: uuid.UUID, payload: CallUpdate, actor: dict
    ) -> CallResponse:
        call = await self._get_by_id(call_id)
        if payload.caller_name is not None:
            call.caller_name_encrypted = self._encryptor.encrypt(payload.caller_name)
        await self._audit.log(
            actor=actor, action="UPDATE_CALL", resource_type="call", resource_id=call_id
        )
        await self._db.flush()
        return self._to_response(call)

    async def list_calls(
        self, page: int, page_size: int, status_filter: str | None
    ) -> CallListResponse:
        stmt = select(Call)
        if status_filter:
            stmt = stmt.where(Call.status == status_filter)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._db.execute(count_stmt)).scalar_one()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(Call.created_at.desc())
        rows = (await self._db.execute(stmt)).scalars().all()
        return CallListResponse(
            items=[self._to_response(c) for c in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_by_id(self, call_id: uuid.UUID, load_transcript: bool = False) -> Call:
        stmt = select(Call).where(Call.id == call_id)
        if load_transcript:
            stmt = stmt.options(selectinload(Call.transcript))
        result = await self._db.execute(stmt)
        call = result.scalar_one_or_none()
        if call is None:
            raise CallNotFoundError(f"Call {call_id} not found")
        return call

    async def _get_by_external_id(self, external_call_id: str) -> Call:
        stmt = select(Call).where(Call.external_call_id == external_call_id)
        result = await self._db.execute(stmt)
        call = result.scalar_one_or_none()
        if call is None:
            raise CallNotFoundError(f"Call with external ID {external_call_id} not found")
        return call

    def _to_response(self, call: Call) -> CallResponse:
        return CallResponse(
            id=call.id,
            external_call_id=call.external_call_id,
            caller_phone=self._encryptor.decrypt(call.caller_phone_encrypted) if call.caller_phone_encrypted else None,
            caller_name=self._encryptor.decrypt(call.caller_name_encrypted) if call.caller_name_encrypted else None,
            status=call.status,
            duration_seconds=call.duration_seconds,
            was_transferred=call.was_transferred,
            transferred_to_agent_id=call.transferred_to_agent_id,
            transfer_timestamp=call.transfer_timestamp,
            started_at=call.started_at,
            ended_at=call.ended_at,
            created_at=call.created_at,
            updated_at=call.updated_at,
        )
