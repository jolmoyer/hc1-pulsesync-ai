"""Anthropic Claude API wrapper."""
import anthropic
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()


class ClaudeClient:
    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(self, system: str, user: str) -> str:
        """Send a prompt to Claude and return the text response."""
        message = await self._client.messages.create(
            model=settings.classification_model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text
