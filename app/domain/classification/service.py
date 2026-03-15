"""ClassificationService — calls Claude to classify a call transcript."""
import json
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.classification import Classification
from app.db.models.queue_item import QueueItem, QueueStatus
from app.domain.classification.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.integrations.ai.claude import ClaudeClient

log = structlog.get_logger(__name__)
settings = get_settings()


class ClassificationResult:
    def __init__(self, classification: str, confidence: float, summary: str) -> None:
        self.classification = classification
        self.confidence = confidence
        self.summary = summary


class ClassificationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._claude = ClaudeClient()

    async def classify_call(self, call_id: uuid.UUID, transcript: str) -> Classification:
        """Call Claude, persist the classification, and create a queue item."""
        result = await self._call_claude(transcript)

        classification = Classification(
            call_id=call_id,
            classification=result.classification,
            confidence=result.confidence,
            ai_summary=result.summary,
            model_version=settings.classification_model,
        )
        self._db.add(classification)

        queue_item = QueueItem(
            call_id=call_id,
            status=QueueStatus.PENDING_REVIEW,
        )
        self._db.add(queue_item)
        await self._db.flush()

        log.info(
            "classification.complete",
            call_id=str(call_id),
            classification=result.classification,
            confidence=result.confidence,
        )
        return classification

    async def _call_claude(self, transcript: str) -> ClassificationResult:
        raw = await self._claude.complete(
            system=SYSTEM_PROMPT,
            user=USER_PROMPT_TEMPLATE.format(transcript=transcript),
        )
        try:
            data = json.loads(raw)
            return ClassificationResult(
                classification=data["classification"],
                confidence=float(data["confidence"]),
                summary=data["summary"],
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            log.error("classification.parse_error", error=str(exc), raw_response=raw)
            return ClassificationResult(
                classification="TASK",
                confidence=0.0,
                summary="AI classification failed. Manual review required.",
            )
