import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.classification import Classification
from app.db.models.queue_item import QueueItem, QueueStatus
from app.schemas.queue import QueueItemResponse, QueueItemUpdate, QueueListResponse


class QueueItemNotFoundError(Exception):
    pass


class QueueService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_items(
        self,
        page: int,
        page_size: int,
        status_filter: str | None,
        assigned_to: uuid.UUID | None,
        classification_filter: str | None,
    ) -> QueueListResponse:
        stmt = select(QueueItem).options(selectinload(QueueItem.call))

        if status_filter:
            stmt = stmt.where(QueueItem.status == status_filter)
        if assigned_to:
            stmt = stmt.where(QueueItem.assigned_to == assigned_to)
        if classification_filter:
            stmt = stmt.join(Classification, Classification.call_id == QueueItem.call_id).where(
                Classification.classification == classification_filter
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._db.execute(count_stmt)).scalar_one()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(
            QueueItem.created_at.desc()
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return QueueListResponse(
            items=[QueueItemResponse.model_validate(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_item(self, item_id: uuid.UUID) -> QueueItemResponse:
        stmt = (
            select(QueueItem)
            .where(QueueItem.id == item_id)
            .options(selectinload(QueueItem.call))
        )
        result = await self._db.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            raise QueueItemNotFoundError(item_id)
        return QueueItemResponse.model_validate(item)

    async def update_item(
        self, item_id: uuid.UUID, payload: QueueItemUpdate, actor: dict
    ) -> QueueItemResponse:
        item = await self._get_orm_item(item_id)

        if payload.status is not None:
            if not QueueStatus.can_transition(item.status, payload.status):
                raise ValueError(
                    f"Cannot transition queue item from {item.status!r} to {payload.status!r}"
                )
            item.status = payload.status

        if payload.reviewer_notes is not None:
            # Persist reviewer_notes on the classification row
            stmt = select(Classification).where(Classification.call_id == item.call_id)
            result = await self._db.execute(stmt)
            classification = result.scalar_one_or_none()
            if classification:
                classification.reviewer_notes = payload.reviewer_notes
                classification.reviewed_by_id = uuid.UUID(actor["sub"])
                classification.reviewed_at = datetime.now(timezone.utc)

        await self._db.flush()
        return QueueItemResponse.model_validate(item)

    async def assign_to_agent(self, item_id: uuid.UUID, agent_id: str) -> QueueItemResponse:
        item = await self._get_orm_item(item_id)
        item.assigned_to = uuid.UUID(agent_id)
        item.assigned_at = datetime.now(timezone.utc)
        if item.status == QueueStatus.PENDING_REVIEW:
            item.status = QueueStatus.IN_REVIEW
        await self._db.flush()
        return QueueItemResponse.model_validate(item)

    async def _get_orm_item(self, item_id: uuid.UUID) -> QueueItem:
        stmt = select(QueueItem).where(QueueItem.id == item_id)
        result = await self._db.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            raise QueueItemNotFoundError(item_id)
        return item
