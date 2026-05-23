from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

from openai import AsyncOpenAI, RateLimitError
from pydantic import SecretStr

from app.models.schemas import ChatMessage
from app.services.llm.base import ProviderRateLimitError, ProviderUnavailableError
from app.services.llm.groq import _secret_value, _to_openai_messages


@dataclass
class OpenRouterProvider:
    model: str
    api_key: SecretStr | None
    name: str = "openrouter"
    rate_limit_remaining: str | None = None

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        api_key = _secret_value(self.api_key)
        if not api_key:
            raise ProviderUnavailableError("OpenRouter API key is not configured.")

        client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        try:
            stream = await client.chat.completions.with_raw_response.create(
                model=self.model,
                messages=_to_openai_messages(messages),
                stream=True,
            )
            self.rate_limit_remaining = stream.headers.get("x-ratelimit-remaining-requests")
            async for chunk in stream.parse():
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except RateLimitError as exc:
            self.rate_limit_remaining = exc.response.headers.get("x-ratelimit-remaining-requests")
            raise ProviderRateLimitError("OpenRouter rate limit exceeded.") from exc
