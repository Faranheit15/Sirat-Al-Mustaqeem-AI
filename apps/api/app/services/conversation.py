from typing import Annotated

from fastapi import Depends

from app.models.schemas import ChatMessage, ConversationSummary
from app.services.supabase import SupabaseService, get_supabase_service


class ConversationService:
    def __init__(self, supabase: SupabaseService) -> None:
        self.supabase = supabase

    async def list_conversations(self, user_id: str) -> list[ConversationSummary]:
        rows = await self.supabase.list_conversations(user_id=user_id)
        return [
            ConversationSummary(
                id=str(row.get("id", "")),
                title=str(row.get("title") or "Untitled conversation"),
                created_at=str(row.get("created_at")) if row.get("created_at") else None,
                updated_at=str(row.get("updated_at", "")),
            )
            for row in rows
        ]

    async def create_conversation(self, user_id: str, title: str) -> ConversationSummary:
        row = await self.supabase.create_conversation(user_id=user_id, title=title)
        if row is None:
            raise RuntimeError("Supabase did not return the created conversation.")

        return ConversationSummary(
            id=str(row.get("id", "")),
            title=str(row.get("title") or title),
            created_at=str(row.get("created_at")) if row.get("created_at") else None,
            updated_at=str(row.get("updated_at", "")),
        )

    async def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        await self.supabase.delete_conversation(user_id=user_id, conversation_id=conversation_id)

    async def list_messages(self, user_id: str, conversation_id: str) -> list[ChatMessage]:
        rows = await self.supabase.list_messages(user_id=user_id, conversation_id=conversation_id)
        return [
            ChatMessage(
                id=str(row.get("id", "")),
                role=row.get("role", "assistant"),
                content=str(row.get("content") or ""),
                created_at=str(row.get("created_at")) if row.get("created_at") else None,
            )
            for row in rows
        ]

    async def save_exchange(
        self,
        user_id: str,
        conversation_id: str | None,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> str | None:
        resolved_conversation_id = conversation_id
        if resolved_conversation_id is None:
            row = await self.supabase.create_conversation(
                user_id=user_id,
                title=user_message.content[:80],
            )
            resolved_conversation_id = str(row.get("id")) if row is not None else None

        if resolved_conversation_id is None:
            return None

        await self.supabase.insert_message(
            conversation_id=resolved_conversation_id,
            user_id=user_id,
            message=user_message,
        )
        await self.supabase.insert_message(
            conversation_id=resolved_conversation_id,
            user_id=user_id,
            message=assistant_message,
        )
        return resolved_conversation_id


SupabaseDependency = Annotated[SupabaseService, Depends(get_supabase_service)]


def get_conversation_service(supabase: SupabaseDependency) -> ConversationService:
    return ConversationService(supabase=supabase)
