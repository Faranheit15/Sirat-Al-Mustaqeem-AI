from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ChatRole = Literal["system", "user", "assistant"]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: ChatRole
    content: str = Field(min_length=1)
    created_at: str | None = None


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    updated_at: str


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class ConversationMessagesResponse(BaseModel):
    messages: list[ChatMessage]


class CreateConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class AuthCallbackRequest(BaseModel):
    event: str
    email: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthCallbackResponse(BaseModel):
    status: Literal["accepted"]
    user_id: str
