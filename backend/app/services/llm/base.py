from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from app.models.schemas import ChatMessage


class LLMProvider(Protocol):
    name: str
    rate_limit_remaining: str | None

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        yield ""


class ProviderUnavailableError(RuntimeError):
    pass


class ProviderRateLimitError(RuntimeError):
    pass
