from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import cast

from openai import AsyncOpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import SecretStr

from app.models.schemas import ChatMessage
from app.services.llm.base import ProviderRateLimitError, ProviderUnavailableError


def _secret_value(secret: SecretStr | None) -> str | None:
    return secret.get_secret_value() if secret is not None else None


def _to_openai_messages(messages: Sequence[ChatMessage]) -> list[ChatCompletionMessageParam]:
    return cast(
        list[ChatCompletionMessageParam],
        [{"role": message.role, "content": message.content} for message in messages],
    )


@dataclass
class GroqProvider:
    model: str
    api_key: SecretStr | None
    name: str = "groq"
    rate_limit_remaining: str | None = None

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        api_key = _secret_value(self.api_key)
        if not api_key:
            raise ProviderUnavailableError("Groq API key is not configured.")

        client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
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
            raise ProviderRateLimitError("Groq rate limit exceeded.") from exc
