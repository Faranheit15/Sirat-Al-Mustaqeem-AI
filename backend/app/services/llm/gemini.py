from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, cast

import google.generativeai as genai
from pydantic import SecretStr

from app.models.schemas import ChatMessage
from app.services.llm.base import ProviderRateLimitError, ProviderUnavailableError
from app.services.llm.groq import _secret_value


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
