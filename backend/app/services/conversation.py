from typing import Annotated

from fastapi import Depends

from app.core.logging import get_logger
from app.models.schemas import ChatMessage, Conversation
from app.services.supabase import SupabaseClient, get_supabase_client

logger = get_logger(__name__)


class ConversationService:
    def __init__(self, supabase: SupabaseClient) -> None:
        self.supabase = supabase

    async def list_conversations(self, user_id: str) -> list[Conversation]:
        rows = await self.supabase.list_conversations(user_id=user_id)
        return [Conversation.model_validate(row) for row in rows]

    async def create_conversation(self, user_id: str, title: str) -> Conversation:
        row = await self.supabase.create_conversation(user_id=user_id, title=title)
        if row is None:
            raise RuntimeError("Supabase did not return the created conversation.")
        conversation = Conversation.model_validate(row)
        logger.info(
            "conversation_created | user_id=%s conversation_id=%s",
            user_id,
            conversation.id,
        )
        return conversation

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

    async def save_exchange(
        self,
        user_id: str,
        conversation_id: str | None,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> str | None:
        resolved_conversation_id = conversation_id
        if resolved_conversation_id is None:
            conversation = await self.create_conversation(
                user_id=user_id,
                title=user_message.content[:80],
            )
            resolved_conversation_id = conversation.id

        await self.supabase.insert_message(resolved_conversation_id, user_message)
        await self.supabase.insert_message(resolved_conversation_id, assistant_message)
        logger.debug(
            "exchange_saved | conversation_id=%s",
            resolved_conversation_id,
        )
        return resolved_conversation_id


SupabaseDependency = Annotated[SupabaseClient, Depends(get_supabase_client)]


def get_conversation_service(supabase: SupabaseDependency) -> ConversationService:
    return ConversationService(supabase=supabase)
