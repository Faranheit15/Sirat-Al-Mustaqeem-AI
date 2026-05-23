from typing import Annotated

from fastapi import Depends

from app.core.logging import get_logger
from app.models.schemas import ChatMessage, Conversation, ConversationWithMessages
from app.services.supabase import SupabaseClient, get_supabase_client

logger = get_logger(__name__)


class ConversationService:
    def __init__(self, supabase: SupabaseClient) -> None:
        self.supabase = supabase

    async def get_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        rows = await self.supabase.list_conversations(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        return [Conversation.model_validate(row) for row in rows]

    async def list_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        return await self.get_conversations(user_id=user_id, limit=limit, offset=offset)

    async def create_conversation(self, user_id: str, title: str | None = None) -> Conversation:
        row = await self.supabase.create_conversation(
            user_id=user_id,
            title=(title or "New conversation").strip()[:120],
        )
        if row is None:
            raise RuntimeError("Supabase did not return the created conversation.")
        conversation = Conversation.model_validate(row)
        logger.info(
            "conversation_created | user_id=%s conversation_id=%s",
            user_id,
            conversation.id,
        )
        return conversation

    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> ConversationWithMessages:
        row = await self.supabase.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )
        if row is None:
            raise LookupError("Conversation not found.")

        messages = await self.list_messages(user_id=user_id, conversation_id=conversation_id)
        return ConversationWithMessages.model_validate({**row, "messages": messages})

    async def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        await self.supabase.delete_conversation(user_id=user_id, conversation_id=conversation_id)
        logger.info(
            "conversation_deleted | user_id=%s conversation_id=%s",
            user_id,
            conversation_id,
        )

    async def list_messages(self, user_id: str, conversation_id: str) -> list[ChatMessage]:
        rows = await self.supabase.list_messages(user_id=user_id, conversation_id=conversation_id)
        return [ChatMessage.model_validate(row) for row in rows]

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[dict[str, object]] | None = None,
    ) -> ChatMessage:
        row = await self.supabase.insert_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations,
        )
        if row is None:
            return ChatMessage(role=role, content=content, citations=citations)
        return ChatMessage.model_validate(row)

    async def save_exchange(
        self,
        user_id: str,
        conversation_id: str | None,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
        title: str | None = None,
    ) -> str | None:
        resolved_conversation_id = conversation_id
        if resolved_conversation_id is None:
            conversation = await self.create_conversation(
                user_id=user_id,
                title=title or user_message.content[:80],
            )
            resolved_conversation_id = conversation.id

        await self.add_message(
            conversation_id=resolved_conversation_id,
            role=user_message.role,
            content=user_message.content,
            citations=user_message.citations,
        )
        await self.add_message(
            conversation_id=resolved_conversation_id,
            role=assistant_message.role,
            content=assistant_message.content,
            citations=assistant_message.citations,
        )
        logger.debug(
            "exchange_saved | conversation_id=%s",
            resolved_conversation_id,
        )
        return resolved_conversation_id


SupabaseDependency = Annotated[SupabaseClient, Depends(get_supabase_client)]


def get_conversation_service(supabase: SupabaseDependency) -> ConversationService:
    return ConversationService(supabase=supabase)
