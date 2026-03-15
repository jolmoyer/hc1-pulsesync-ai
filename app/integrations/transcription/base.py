from abc import ABC, abstractmethod


class TranscriptionProvider(ABC):
    @abstractmethod
    async def submit_job(self, recording_url: str, callback_url: str) -> str:
        """Submit an audio file for transcription. Returns provider job ID."""

    @abstractmethod
    async def get_transcript(self, job_id: str) -> str | None:
        """Poll for a completed transcript. Returns None if not ready."""
