import httpx
import structlog

from app.config import get_settings
from app.integrations.crm.base import CRMClient, CRMRecord

log = structlog.get_logger(__name__)
settings = get_settings()


class HC1CRMClient(CRMClient):
    def __init__(self) -> None:
        self._base_url = settings.hc1_crm_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.hc1_crm_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._timeout = settings.hc1_crm_timeout_seconds

    async def create_case(self, payload: dict) -> CRMRecord:
        return await self._post("/cases", payload, "CASE")

    async def create_task(self, payload: dict) -> CRMRecord:
        return await self._post("/tasks", payload, "TASK")

    async def _post(self, path: str, payload: dict, record_type: str) -> CRMRecord:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}{path}",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            record_id = str(data.get("id") or data.get("record_id") or "")
            log.info("crm.record_created", type=record_type, record_id=record_id)
            return CRMRecord(
                record_id=record_id,
                record_type=record_type,
                url=data.get("url"),
            )
