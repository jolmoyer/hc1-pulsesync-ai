from fastapi import APIRouter

from app.api.v1 import agents, auth, calls, queue, sync

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(calls.router)
router.include_router(queue.router)
router.include_router(sync.router)
router.include_router(agents.router)
