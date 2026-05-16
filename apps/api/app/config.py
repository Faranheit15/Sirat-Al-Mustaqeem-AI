from functools import lru_cache

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")
    database_url: str = Field(default="", alias="DATABASE_URL")
    cors_origins_raw: str = Field(default="http://localhost:3000", alias="API_CORS_ORIGINS")

    supabase_url: AnyHttpUrl | None = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: SecretStr | None = Field(default=None, alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: SecretStr | None = Field(
        default=None, alias="SUPABASE_SERVICE_ROLE_KEY"
    )
    supabase_jwt_audience: str = Field(default="authenticated", alias="SUPABASE_JWT_AUDIENCE")

    groq_api_key: SecretStr | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    openrouter_api_key: SecretStr | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="meta-llama/llama-3.1-70b-instruct",
        alias="OPENROUTER_MODEL",
    )

    rate_limit_requests_per_minute: int = Field(default=20, alias="RATE_LIMIT_REQUESTS_PER_MINUTE")
    jwks_cache_ttl_seconds: int = Field(default=3600, alias="JWKS_CACHE_TTL_SECONDS")

    @field_validator("rate_limit_requests_per_minute", "jwks_cache_ttl_seconds")
    @classmethod
    def must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("value must be positive")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    @property
    def supabase_jwks_url(self) -> str:
        if self.supabase_url is None:
            raise RuntimeError("SUPABASE_URL is required for JWT verification.")
        return f"{str(self.supabase_url).rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def supabase_jwt_issuer(self) -> str:
        if self.supabase_url is None:
            raise RuntimeError("SUPABASE_URL is required for JWT verification.")
        return f"{str(self.supabase_url).rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
