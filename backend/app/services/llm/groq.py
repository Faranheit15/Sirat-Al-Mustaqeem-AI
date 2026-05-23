from dataclasses import dataclass

from pydantic import SecretStr

from app.services.llm.openai_compatible import OpenAICompatibleProvider


@dataclass
class GroqProvider(OpenAICompatibleProvider):
    def __init__(self, model: str, api_key: SecretStr | None) -> None:
        super().__init__(
            name="groq",
            model=model,
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
