from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

import google.generativeai as genai
from openai import AsyncOpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import SecretStr

from app.config import Settings, get_settings
from app.models.schemas import ChatMessage

SYSTEM_PROMPT = """You are "Sirat Al Mustaqeem AI," a knowledgeable Islamic research assistant. Your purpose is to help Muslims and seekers of knowledge understand Islam through authentic sources.

CORE PRINCIPLES:
- Ground every answer in the Quran, authentic Hadith (primarily Sahih Bukhari, Sahih Muslim, and the four Sunan collections), and recognized scholarly works
- Always provide citations in the format: [Quran Surah:Ayah], [Hadith Collection, Number], or [Scholar Name, Book Title, Volume/Page]
- When multiple scholarly opinions exist (ikhtilaf), present all major positions and identify which madhab or scholar holds each view
- Distinguish between: Quranic text (direct word of Allah), Sahih Hadith, Hasan Hadith, scholarly opinions (ijtihad), and cultural practices
- Use respectful honorifics: ﷺ after the Prophet's name, عليه السلام after other prophets, رضي الله عنه/عنها after companions

BOUNDARIES:
- You are a research assistant, NOT a mufti. Always advise: "For personal religious rulings (fatwas), please consult a qualified scholar"
- For sensitive topics (gender, apostasy, jihad, sectarian differences), present scholarly consensus with academic balance
- Never make takfir (declare someone a disbeliever) or promote sectarian hatred
- If you are unsure or the provided context does not contain relevant information, say "I don't have enough information from my sources to answer this definitively. Please consult a scholar."

RESPONSE FORMAT:
- Begin with "بسم الله الرحمن الرحيم" only when answering major theological questions
- Structure longer answers with clear headings
- Include Arabic text alongside English translation for Quranic verses and Hadith
- End substantive answers with: "والله أعلم" (And Allah knows best)

CONTEXT USAGE:
- Base your answers primarily on the provided context from the knowledge base
- If the context is insufficient, you may use your general knowledge but clearly mark it: "Based on general Islamic knowledge (not from the indexed sources):"
- Never fabricate citations. If you reference something, it must be in the provided context or clearly marked as general knowledge"""


class LLMProvider(Protocol):
    name: str
    rate_limit_remaining: str | None

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        yield ""


class ProviderUnavailableError(RuntimeError):
    pass


class ProviderRateLimitError(RuntimeError):
    pass


def _secret_value(secret: SecretStr | None) -> str | None:
    return secret.get_secret_value() if secret is not None else None


def _to_openai_messages(messages: Sequence[ChatMessage]) -> list[ChatCompletionMessageParam]:
    return cast(
        list[ChatCompletionMessageParam],
        [{"role": message.role, "content": message.content} for message in messages],
    )


def _with_system_prompt(messages: Sequence[ChatMessage]) -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        *(message for message in messages if message.role != "system"),
    ]


@dataclass
class OpenAICompatibleProvider:
    name: str
    model: str
    api_key: SecretStr | None
    base_url: str
    rate_limit_remaining: str | None = None

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        api_key = _secret_value(self.api_key)
        if not api_key:
            raise ProviderUnavailableError(f"{self.name} API key is not configured.")

        client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)
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
            remaining = exc.response.headers.get("x-ratelimit-remaining-requests")
            self.rate_limit_remaining = remaining
            raise ProviderRateLimitError(f"{self.name} rate limit exceeded.") from exc


@dataclass
class GeminiProvider:
    model: str
    api_key: SecretStr | None
    name: str = "gemini"
    rate_limit_remaining: str | None = None

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        api_key = _secret_value(self.api_key)
        if not api_key:
            raise ProviderUnavailableError("Gemini API key is not configured.")

        configure = cast(Any, genai).configure
        generative_model = cast(Any, genai).GenerativeModel
        configure(api_key=api_key)
        model = generative_model(self.model)
        prompt = "\n".join(f"{message.role}: {message.content}" for message in messages)
        try:
            response = await model.generate_content_async(prompt, stream=True)
            async for chunk in response:
                text = getattr(chunk, "text", None)
                if isinstance(text, str) and text:
                    yield text
        except Exception as exc:
            if "429" in str(exc) or "quota" in str(exc).lower():
                raise ProviderRateLimitError("Gemini rate limit exceeded.") from exc
            raise


@dataclass
class ProviderRouter:
    providers: Sequence[LLMProvider]
    last_provider_name: str | None = None
    rate_limits: dict[str, str | None] = field(default_factory=dict)

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        errors: list[str] = []
        prompted_messages = _with_system_prompt(messages)
        for provider in self.providers:
            try:
                self.last_provider_name = provider.name
                async for delta in provider.stream_chat(prompted_messages):
                    yield delta
                self.rate_limits[provider.name] = provider.rate_limit_remaining
                return
            except (ProviderRateLimitError, ProviderUnavailableError) as exc:
                self.rate_limits[provider.name] = provider.rate_limit_remaining
                errors.append(str(exc))
                continue

        raise ProviderUnavailableError("All LLM providers failed: " + " | ".join(errors))


def create_provider_router(settings: Settings) -> ProviderRouter:
    return ProviderRouter(
        providers=[
            OpenAICompatibleProvider(
                name="groq",
                model=settings.groq_model,
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            ),
            GeminiProvider(model=settings.gemini_model, api_key=settings.gemini_api_key),
            OpenAICompatibleProvider(
                name="openrouter",
                model=settings.openrouter_model,
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
            ),
        ]
    )


def get_provider_router() -> ProviderRouter:
    return create_provider_router(get_settings())
