from typing import Annotated, Any, cast

import anyio
from fastapi import Depends
from supabase import Client, create_client

from app.config import Settings, get_settings
from app.models.schemas import ChatMessage


class SupabaseService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        if self._client is None:
            if (
                self.settings.supabase_url is None
                or self.settings.supabase_service_role_key is None
            ):
                raise RuntimeError("Supabase URL and service role key are required.")
            self._client = create_client(
                str(self.settings.supabase_url),
                self.settings.supabase_service_role_key.get_secret_value(),
            )
        return self._client

    async def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        def query() -> list[dict[str, Any]]:
            response = (
                self.client.table("conversations")
                .select("id,user_id,title,created_at,updated_at")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .execute()
            )
            data = response.data
            if not isinstance(data, list):
                return []
            return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

        return await anyio.to_thread.run_sync(query)

    async def create_conversation(self, user_id: str, title: str) -> dict[str, Any] | None:
        def query() -> dict[str, Any] | None:
            response = (
                self.client.table("conversations")
                .insert({"user_id": user_id, "title": title})
                .execute()
            )
            data = response.data
            if isinstance(data, list) and data and isinstance(data[0], dict):
                return cast(dict[str, Any], data[0])
            return None

        return await anyio.to_thread.run_sync(query)

    async def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        def query() -> None:
            self.client.table("conversations").delete().eq("id", conversation_id).eq(
                "user_id", user_id
            ).execute()

        await anyio.to_thread.run_sync(query)

    async def list_messages(self, user_id: str, conversation_id: str) -> list[dict[str, Any]]:
        def query() -> list[dict[str, Any]]:
            conversation_response = (
                self.client.table("conversations")
                .select("id")
                .eq("id", conversation_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if not conversation_response.data:
                return []

            response = (
                self.client.table("messages")
                .select("id,conversation_id,role,content,created_at")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=False)
                .execute()
            )
            data = response.data
            if not isinstance(data, list):
                return []
            return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

        return await anyio.to_thread.run_sync(query)

    async def insert_message(
        self,
        conversation_id: str,
        user_id: str,
        message: ChatMessage,
    ) -> None:
        def query() -> None:
            self.client.table("messages").insert(
                {
                    "conversation_id": conversation_id,
                    "role": message.role,
                    "content": message.content,
                }
            ).execute()

        await anyio.to_thread.run_sync(query)

    async def upsert_user_profile(
        self,
        user_id: str,
        email: str | None,
        metadata: dict[str, Any],
    ) -> None:
        def query() -> None:
            self.client.table("profiles").upsert(
                {
                    "id": user_id,
                    "email": email,
                    "metadata": metadata,
                }
            ).execute()

        await anyio.to_thread.run_sync(query)


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_supabase_service(settings: SettingsDependency) -> SupabaseService:
    return SupabaseService(settings=settings)
