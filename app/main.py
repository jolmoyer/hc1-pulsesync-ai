"""hc1 PulseSync AI — FastAPI application factory."""
import time

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.api.webhooks.telephony import router as telephony_router
from app.api.webhooks.transcription import router as transcription_router
from app.config import get_settings
from app.db.session import engine

log = structlog.get_logger(__name__)
settings = get_settings()

# ── App factory ───────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    app = FastAPI(
        title="hc1 PulseSync AI",
        description="Healthcare AI voice support backend",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    _register_middleware(app)
    _register_routers(app)
    _register_exception_handlers(app)

    return app


def _register_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logger(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response


def _register_routers(app: FastAPI) -> None:
    app.include_router(v1_router)
    app.include_router(telephony_router)
    app.include_router(transcription_router)


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )


# ── Health endpoints ──────────────────────────────────────────────────────────

app = create_app()


@app.get("/health", tags=["health"], summary="Liveness probe")
async def health_live() -> dict:
    """Returns 200 when the process is running."""
    return {"status": "ok", "service": "hc1-pulsesync-ai"}


@app.get("/health/ready", tags=["health"], summary="Readiness probe")
async def health_ready() -> JSONResponse:
    """Returns 200 when the app is ready to serve traffic.
    Checks database connectivity."""
    checks: dict[str, str] = {}
    all_ok = True

    # Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        all_ok = False

    # Redis check
    try:
        import redis.asyncio as aioredis
        r = await aioredis.from_url(str(settings.redis_url), socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        all_ok = False

    http_status = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )
