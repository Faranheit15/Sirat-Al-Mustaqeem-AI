from dataclasses import dataclass

from pydantic import SecretStr

from app.services.llm.openai_compatible import OpenAICompatibleProvider


@dataclass
class GeminiProvider(OpenAICompatibleProvider):
    def __init__(self, model: str, api_key: SecretStr | None) -> None:
        super().__init__(
            name="gemini",
            model=model,
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
