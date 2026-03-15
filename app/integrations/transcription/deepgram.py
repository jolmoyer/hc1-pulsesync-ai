import httpx
import structlog

from app.config import get_settings
from app.integrations.transcription.base import TranscriptionProvider

log = structlog.get_logger(__name__)
settings = get_settings()

_DEEPGRAM_API_URL = "https://api.deepgram.com/v1"


class DeepgramProvider(TranscriptionProvider):
    def __init__(self) -> None:
        self._headers = {
            "Authorization": f"Token {settings.deepgram_api_key}",
            "Content-Type": "application/json",
        }

    async def submit_job(self, recording_url: str, callback_url: str) -> str:
        """Download audio from Twilio (requires auth) then submit bytes to Deepgram."""
        from app.config import get_settings
        cfg = get_settings()

        # Download audio from Twilio using basic auth
        async with httpx.AsyncClient(timeout=60) as client:
            audio_response = await client.get(
                recording_url,
                auth=(cfg.twilio_account_sid, cfg.twilio_auth_token),
            )
            audio_response.raise_for_status()
            audio_bytes = audio_response.content

        # Submit raw audio bytes to Deepgram
        headers = {
            "Authorization": f"Token {settings.deepgram_api_key}",
            "Content-Type": "audio/wav",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{_DEEPGRAM_API_URL}/listen",
                headers=headers,
                params={
                    "callback": callback_url,
                    "model": "nova-2",
                    "smart_format": "true",
                    "punctuate": "true",
                },
                content=audio_bytes,
            )
            response.raise_for_status()
            data = response.json()
            job_id: str = data["request_id"]
            log.info("transcription.job_submitted", job_id=job_id)
            return job_id

    async def get_transcript(self, job_id: str) -> str | None:
        """Poll Deepgram for a completed transcript (fallback if callback missed)."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{_DEEPGRAM_API_URL}/requests/{job_id}",
                headers=self._headers,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "completed":
                return None
            channels = data.get("results", {}).get("channels", [])
            if channels:
                alts = channels[0].get("alternatives", [])
                if alts:
                    return alts[0].get("transcript", "")
            return None
