from dataclasses import dataclass

from pydantic import SecretStr

from app.services.llm.openai_compatible import OpenAICompatibleProvider


@dataclass
class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, model: str, api_key: SecretStr | None) -> None:
        super().__init__(
            name="openrouter",
            model=model,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            extra_headers={
                "HTTP-Referer": "https://sirat-al-mustaqeem.ai",
                "X-Title": "Sirat Al Mustaqeem AI",
            },
        )
