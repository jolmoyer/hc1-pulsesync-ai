from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CRMRecord:
    record_id: str
    record_type: str  # CASE | TASK
    url: str | None = None


class CRMClient(ABC):
    @abstractmethod
    async def create_case(self, payload: dict) -> CRMRecord:
        """Create a Case in the CRM. Returns the created record reference."""

    @abstractmethod
    async def create_task(self, payload: dict) -> CRMRecord:
        """Create a Task in the CRM. Returns the created record reference."""
