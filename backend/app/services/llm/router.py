from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field

from app.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.schemas import ChatMessage
from app.services.llm.base import LLMProvider, ProviderRateLimitError, ProviderUnavailableError
from app.services.llm.gemini import GeminiProvider
from app.services.llm.groq import GroqProvider
from app.services.llm.openrouter import OpenRouterProvider

logger = get_logger(__name__)

SYSTEM_PROMPT = "\n".join(
    [
        'You are "Sirat Al Mustaqeem AI," a knowledgeable Islamic research assistant.',
        "Your purpose is to help Muslims and seekers of knowledge understand Islam through",
        "authentic sources.",
        "",
        "CORE PRINCIPLES:",
        "- Ground every answer in the Quran, authentic Hadith (primarily Sahih Bukhari,",
        "  Sahih Muslim, and the four Sunan collections), and recognized scholarly works",
        "- Always provide citations in the format: [Quran Surah:Ayah],",
        "  [Hadith Collection, Number], or [Scholar Name, Book Title, Volume/Page]",
        "- When multiple scholarly opinions exist (ikhtilaf), present all major positions",
        "  and identify which madhab or scholar holds each view",
        "- Distinguish between: Quranic text (direct word of Allah), Sahih Hadith,",
        "  Hasan Hadith, scholarly opinions (ijtihad), and cultural practices",
        "- Use respectful honorifics: ﷺ after the Prophet's name, عليه السلام after",
        "  other prophets, رضي الله عنه/عنها after companions",
        "",
        "BOUNDARIES:",
        '- You are a research assistant, NOT a mufti. Always advise: "For personal',
        '  religious rulings (fatwas), please consult a qualified scholar"',
        "- For sensitive topics (gender, apostasy, jihad, sectarian differences), present",
        "  scholarly consensus with academic balance",
        "- Never make takfir (declare someone a disbeliever) or promote sectarian hatred",
        "- If you are unsure or the provided context does not contain relevant information,",
        "  say \"I don't have enough information from my sources to answer this",
        '  definitively. Please consult a scholar."',
        "",
        "RESPONSE FORMAT:",
        '- Begin with "بسم الله الرحمن الرحيم" only when answering major theological',
        "  questions",
        "- Structure longer answers with clear headings",
        "- Include Arabic text alongside English translation for Quranic verses and Hadith",
        '- End substantive answers with: "والله أعلم" (And Allah knows best)',
        "",
        "CONTEXT USAGE:",
        "- Base your answers primarily on the provided context from the knowledge base",
        "- If the context is insufficient, you may use your general knowledge but clearly",
        '  mark it: "Based on general Islamic knowledge (not from the indexed sources):"',
        "- Never fabricate citations. If you reference something, it must be in the",
        "  provided context or clearly marked as general knowledge",
    ]
)


def _with_system_prompt(messages: Sequence[ChatMessage]) -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        *(message for message in messages if message.role != "system"),
    ]


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
                logger.info("llm_attempt | provider=%s", provider.name)
                async for delta in provider.stream_chat(prompted_messages):
                    yield delta
                self.rate_limits[provider.name] = provider.rate_limit_remaining
                logger.debug(
                    "llm_success | provider=%s rate_limit_remaining=%s",
                    provider.name,
                    provider.rate_limit_remaining,
                )
                return
            except (ProviderRateLimitError, ProviderUnavailableError) as exc:
                self.rate_limits[provider.name] = provider.rate_limit_remaining
                errors.append(str(exc))
                logger.warning(
                    "llm_failover | provider=%s reason=%s",
                    provider.name,
                    exc,
                )
                continue

        logger.error("llm_all_failed | errors=%s", " | ".join(errors))
        raise ProviderUnavailableError("All LLM providers failed: " + " | ".join(errors))


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
