from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

ChatRole = Literal["system", "user", "assistant"]
LLMProviderName = Literal["groq", "gemini", "openrouter"]


class ApiEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: Any = None
    error: str | None = None
    message: str | None = None


class HealthData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: str
    version: str
    environment: str
    auth_required: bool
    client: dict[str, Any]


class HealthResponse(ApiEnvelope):
    data: HealthData


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    role: ChatRole
    content: str = Field(min_length=1)
    citations: list[dict[str, Any]] | None = None
    created_at: str | None = None


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str | None = Field(
        default=None,
        description="Existing conversation id. Omit or use null to start a new conversation.",
        examples=[None],
    )
    messages: list[ChatMessage] = Field(min_length=1)

    @field_validator("conversation_id", mode="before")
    @classmethod
    def normalize_swagger_placeholder(cls, value: object) -> object:
        if isinstance(value, str) and value.strip().lower() in {"", "string", "null", "none"}:
            return None
        return value


class Conversation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: str | None = None
    title: str
    created_at: str | None = None
    updated_at: str | None = None


class ConversationWithMessages(Conversation):
    messages: list[ChatMessage] = Field(default_factory=list)


class ConversationListData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversations: list[Conversation]


class ConversationListResponse(ApiEnvelope):
    data: ConversationListData


class ConversationMessagesData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage]


class ConversationMessagesResponse(ApiEnvelope):
    data: ConversationMessagesData


class CreateConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=120)


class ConversationResponse(ApiEnvelope):
    data: Conversation


class ConversationDetailResponse(ApiEnvelope):
    data: ConversationWithMessages


class LLMProviderStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: LLMProviderName
    available: bool
    rate_limit_remaining: str | None = None
