from functools import lru_cache

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")
    api_title: str = Field(default="Sirat Al Mustaqeem AI API", alias="API_TITLE")
    api_version: str = Field(default="0.1.0", alias="API_VERSION")
    cors_origins_raw: str = Field(default="http://localhost:3000", alias="API_CORS_ORIGINS")
    auth_required: bool | None = Field(default=None, alias="AUTH_REQUIRED")
    local_dev_user_id: str = Field(
        default="00000000-0000-4000-8000-000000000000",
        alias="LOCAL_DEV_USER_ID",
    )
    local_dev_user_email: str = Field(
        default="local-dev@sirat.local",
        alias="LOCAL_DEV_USER_EMAIL",
    )

    supabase_url: AnyHttpUrl | None = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: SecretStr | None = Field(default=None, alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: SecretStr | None = Field(
        default=None,
        alias="SUPABASE_SERVICE_ROLE_KEY",
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
    http_timeout_seconds: int = Field(default=30, alias="HTTP_TIMEOUT_SECONDS")

    @field_validator(
        "rate_limit_requests_per_minute",
        "jwks_cache_ttl_seconds",
        "http_timeout_seconds",
    )
    @classmethod
    def must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("value must be positive")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    @property
    def is_local_environment(self) -> bool:
        return self.environment.lower() in {"local", "dev", "development", "test"}

    @property
    def should_require_auth(self) -> bool:
        if self.auth_required is not None:
            return self.auth_required
        return not self.is_local_environment

    @property
    def supabase_base_url(self) -> str:
        if self.supabase_url is None:
            raise RuntimeError("SUPABASE_URL is required.")
        return str(self.supabase_url).rstrip("/")

    @property
    def supabase_rest_url(self) -> str:
        return f"{self.supabase_base_url}/rest/v1"

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_base_url}/auth/v1/.well-known/jwks.json"

    @property
    def supabase_jwt_issuer(self) -> str:
        return f"{self.supabase_base_url}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
