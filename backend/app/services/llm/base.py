from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from app.models.schemas import ChatMessage


class LLMProvider(Protocol):
    name: str
    model: str
    rate_limit_remaining: str | None

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        yield ""

    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        return ""

    def check_rate_limit(self) -> bool:
        return True


class ProviderUnavailableError(RuntimeError):
    pass


class ProviderRateLimitError(RuntimeError):
    pass
