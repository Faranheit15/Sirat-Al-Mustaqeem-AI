from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import cast

from openai import APIStatusError, AsyncOpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import SecretStr

from app.core.logging import get_logger
from app.models.schemas import ChatMessage
from app.services.llm.base import ProviderRateLimitError, ProviderUnavailableError

logger = get_logger(__name__)


def secret_value(secret: SecretStr | None) -> str | None:
    return secret.get_secret_value() if secret is not None else None


def to_openai_messages(messages: Sequence[ChatMessage]) -> list[ChatCompletionMessageParam]:
    return cast(
        list[ChatCompletionMessageParam],
        [{"role": message.role, "content": message.content} for message in messages],
    )


@dataclass
class OpenAICompatibleProvider:
    name: str
    model: str
    api_key: SecretStr | None
    base_url: str
    rate_limit_remaining: str | None = None

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        api_key = secret_value(self.api_key)
        if not api_key:
            logger.warning("provider_unavailable | provider=%s reason=api_key_missing", self.name)
            raise ProviderUnavailableError(f"{self.name} API key is not configured.")

        logger.info("provider_stream_start | provider=%s model=%s", self.name, self.model)
        client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)
        try:
            stream = await client.chat.completions.with_raw_response.create(
                model=self.model,
                messages=to_openai_messages(messages),
                stream=True,
            )
            self.rate_limit_remaining = stream.headers.get("x-ratelimit-remaining-requests")
            logger.debug(
                "provider_rate_limit | provider=%s remaining=%s",
                self.name,
                self.rate_limit_remaining,
            )
            async for chunk in stream.parse():
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except RateLimitError as exc:
            self.rate_limit_remaining = exc.response.headers.get("x-ratelimit-remaining-requests")
            logger.warning(
                "provider_rate_limited | provider=%s remaining=%s",
                self.name,
                self.rate_limit_remaining,
            )
            raise ProviderRateLimitError(f"{self.name} rate limit exceeded.") from exc
        except APIStatusError as exc:
            if exc.status_code == 429:
                self.rate_limit_remaining = exc.response.headers.get(
                    "x-ratelimit-remaining-requests"
                )
                logger.warning(
                    "provider_rate_limited | provider=%s status=429 remaining=%s",
                    self.name,
                    self.rate_limit_remaining,
                )
                raise ProviderRateLimitError(f"{self.name} rate limit exceeded.") from exc
            logger.error(
                "provider_api_error | provider=%s status=%s message=%s",
                self.name,
                exc.status_code,
                exc.message,
            )
            raise
