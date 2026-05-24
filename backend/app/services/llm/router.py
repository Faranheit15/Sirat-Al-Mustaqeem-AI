import asyncio
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field

from app.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.schemas import ChatMessage
from app.services.llm.base import LLMProvider, ProviderRateLimitError, ProviderUnavailableError
from app.services.llm.gemini import GeminiProvider
from app.services.llm.groq import GroqProvider
from app.services.llm.openrouter import OpenRouterProvider
from app.services.llm.prompts import SYSTEM_PROMPT

logger = get_logger(__name__)

_INITIAL_RETRY_DELAY = 1.0  # seconds; doubles on each successive retry


def _with_system_prompt(
    messages: Sequence[ChatMessage],
    context: str | None = None,
) -> list[ChatMessage]:
    system_content = SYSTEM_PROMPT if not context else f"{SYSTEM_PROMPT}\n\n{context}"
    return [
        ChatMessage(role="system", content=system_content),
        *(message for message in messages if message.role != "system"),
    ]


@dataclass
class ProviderRouter:
    providers: Sequence[LLMProvider]
    last_provider_name: str | None = None
    rate_limits: dict[str, str | None] = field(default_factory=dict)

    async def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        context: str | None = None,
    ) -> AsyncIterator[str]:
        errors: list[str] = []
        prompted_messages = _with_system_prompt(messages, context=context)
        retry_count = 0
        retry_delay = _INITIAL_RETRY_DELAY

        for provider in self.providers:
            if not provider.check_rate_limit():
                logger.info(
                    "provider_skipped | provider=%s reason=rate_limit_cache",
                    provider.name,
                )
                continue

            if retry_count > 0:
                logger.debug(
                    "llm_retry_backoff | provider=%s delay=%.1fs",
                    provider.name,
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2

            try:
                self.last_provider_name = provider.name
                logger.info(
                    "llm_attempt | provider=%s model=%s",
                    provider.name,
                    provider.model,
                )
                async for delta in provider.stream_chat(prompted_messages):
                    yield delta
                self.rate_limits[provider.name] = provider.rate_limit_remaining
                logger.info(
                    "llm_success | provider=%s model=%s rate_limit_remaining=%s",
                    provider.name,
                    provider.model,
                    provider.rate_limit_remaining,
                )
                return
            except (ProviderRateLimitError, ProviderUnavailableError) as exc:
                self.rate_limits[provider.name] = provider.rate_limit_remaining
                errors.append(str(exc))
                retry_count += 1
                logger.warning(
                    "llm_failover | provider=%s model=%s reason=%s",
                    provider.name,
                    provider.model,
                    exc,
                )
                continue

        logger.error("llm_all_failed | errors=%s", " | ".join(errors))
        raise ProviderUnavailableError("All LLM providers failed: " + " | ".join(errors))

    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        errors: list[str] = []
        retry_count = 0
        retry_delay = _INITIAL_RETRY_DELAY

        for provider in self.providers:
            if not provider.check_rate_limit():
                logger.info(
                    "provider_skipped | provider=%s reason=rate_limit_cache",
                    provider.name,
                )
                continue

            if retry_count > 0:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2

            try:
                self.last_provider_name = provider.name
                logger.info(
                    "llm_complete_attempt | provider=%s model=%s",
                    provider.name,
                    provider.model,
                )
                content = await provider.complete(messages)
                self.rate_limits[provider.name] = provider.rate_limit_remaining
                logger.info("llm_complete_success | provider=%s", provider.name)
                return content
            except (ProviderRateLimitError, ProviderUnavailableError) as exc:
                self.rate_limits[provider.name] = provider.rate_limit_remaining
                errors.append(str(exc))
                retry_count += 1
                logger.warning(
                    "llm_complete_failover | provider=%s model=%s reason=%s",
                    provider.name,
                    provider.model,
                    exc,
                )
                continue

        logger.error("llm_complete_all_failed | errors=%s", " | ".join(errors))
        raise ProviderUnavailableError("All LLM providers failed: " + " | ".join(errors))

    async def generate_title(self, first_message: str) -> str:
        title = await self.complete(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "Summarize the user's chat topic as a short conversation title. "
                        "Return only the title, maximum five words."
                    ),
                ),
                ChatMessage(role="user", content=first_message[:1000]),
            ]
        )
        cleaned = title.strip().strip('"').strip("'")
        return cleaned[:80] or first_message[:80] or "New conversation"


def create_provider_router(settings: Settings) -> ProviderRouter:
    return ProviderRouter(
        providers=[
            GroqProvider(model=settings.groq_model, api_key=settings.groq_api_key),
            GeminiProvider(model=settings.gemini_model, api_key=settings.gemini_api_key),
            OpenRouterProvider(
                model=settings.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
        ]
    )


def get_provider_router() -> ProviderRouter:
    return create_provider_router(get_settings())
