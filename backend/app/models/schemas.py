from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

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
    created_at: str | None = None


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)


class Conversation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: str | None = None
    title: str
    created_at: str | None = None
    updated_at: str | None = None


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

    title: str = Field(min_length=1, max_length=120)


class ConversationResponse(ApiEnvelope):
    data: Conversation


class LLMProviderStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: LLMProviderName
    available: bool
    rate_limit_remaining: str | None = None
