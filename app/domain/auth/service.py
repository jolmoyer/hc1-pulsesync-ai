"""AuthService — agent authentication, JWT lifecycle, and RBAC."""
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentListResponse, AgentResponse, AgentUpdate
from app.schemas.auth import AccessTokenResponse, TokenResponse

log = structlog.get_logger(__name__)
settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AgentNotFoundError(Exception):
    pass


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Authentication ────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> TokenResponse | None:
        agent = await self._get_agent_by_email(email)
        if agent is None or not agent.is_active:
            return None
        if not _pwd_context.verify(password, agent.hashed_password):
            return None
        return TokenResponse(
            access_token=self._create_access_token(agent),
            refresh_token=self._create_refresh_token(agent),
        )

    async def refresh_access_token(self, refresh_token: str) -> AccessTokenResponse | None:
        payload = self._decode_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            return None
        agent = await self._get_agent_by_id(uuid.UUID(payload["sub"]))
        if agent is None or not agent.is_active:
            return None
        return AccessTokenResponse(access_token=self._create_access_token(agent))

    async def logout(self, refresh_token: str) -> None:
        # Stateless JWT — in production, add the jti to a Redis blocklist here.
        log.info("auth.logout")

    async def verify_access_token(self, token: str) -> dict | None:
        payload = self._decode_token(token)
        if payload is None or payload.get("type") != "access":
            return None
        return payload

    # ── Agent CRUD ────────────────────────────────────────────────────────────

    async def create_agent(self, payload: AgentCreate) -> AgentResponse:
        existing = await self._get_agent_by_email(payload.email)
        if existing is not None:
            raise ValueError(f"Agent with email {payload.email} already exists")
        agent = Agent(
            name=payload.name,
            email=payload.email,
            hashed_password=_pwd_context.hash(payload.password),
            role=payload.role,
            external_id=payload.external_id,
        )
        self._db.add(agent)
        await self._db.flush()
        return AgentResponse.model_validate(agent)

    async def get_agent(self, agent_id: uuid.UUID) -> AgentResponse:
        agent = await self._get_agent_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(agent_id)
        return AgentResponse.model_validate(agent)

    async def list_agents(self, page: int, page_size: int) -> AgentListResponse:
        count_stmt = select(func.count()).select_from(Agent)
        total = (await self._db.execute(count_stmt)).scalar_one()
        stmt = (
            select(Agent)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(Agent.created_at.desc())
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return AgentListResponse(
            items=[AgentResponse.model_validate(a) for a in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_agent(self, agent_id: uuid.UUID, payload: AgentUpdate) -> AgentResponse:
        agent = await self._get_agent_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(agent_id)
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(agent, field, value)
        await self._db.flush()
        return AgentResponse.model_validate(agent)

    async def deactivate_agent(self, agent_id: uuid.UUID) -> None:
        agent = await self._get_agent_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(agent_id)
        agent.is_active = False
        await self._db.flush()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _create_access_token(self, agent: Agent) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        return jwt.encode(
            {"sub": str(agent.id), "role": agent.role, "type": "access", "exp": expire},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    def _create_refresh_token(self, agent: Agent) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
        return jwt.encode(
            {"sub": str(agent.id), "type": "refresh", "exp": expire},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    def _decode_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except JWTError:
            return None

    async def _get_agent_by_email(self, email: str) -> Agent | None:
        stmt = select(Agent).where(Agent.email == email)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_agent_by_id(self, agent_id: uuid.UUID) -> Agent | None:
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()
