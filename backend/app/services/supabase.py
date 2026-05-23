from typing import Annotated, Any, cast

import httpx
from fastapi import Depends

from app.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.schemas import ChatMessage

logger = get_logger(__name__)


class SupabaseClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _service_headers(self) -> dict[str, str]:
        if self.settings.supabase_service_role_key is None:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required.")
        key = self.settings.supabase_service_role_key.get_secret_value()
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: Any | None = None,
        prefer: str | None = None,
    ) -> Any:
        headers = self._service_headers()
        if prefer is not None:
            headers["Prefer"] = prefer

        url = f"{self.settings.supabase_rest_url}{path}"
        logger.debug("supabase_request | method=%s path=%s", method, path)

        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            try:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "supabase_error | method=%s path=%s status=%s",
                    method,
                    path,
                    exc.response.status_code,
                )
                raise
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

    async def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/conversations",
            params={
                "select": "id,user_id,title,created_at,updated_at",
                "user_id": f"eq.{user_id}",
                "order": "updated_at.desc",
            },
        )
        return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

    async def create_conversation(self, user_id: str, title: str) -> dict[str, Any] | None:
        data = await self._request(
            "POST",
            "/conversations",
            json_body={"user_id": user_id, "title": title},
            prefer="return=representation",
        )
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return cast(dict[str, Any], data[0])
        return None

    async def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        await self._request(
            "DELETE",
            "/conversations",
            params={"id": f"eq.{conversation_id}", "user_id": f"eq.{user_id}"},
        )

    async def list_messages(self, user_id: str, conversation_id: str) -> list[dict[str, Any]]:
        conversations = await self._request(
            "GET",
            "/conversations",
            params={"select": "id", "id": f"eq.{conversation_id}", "user_id": f"eq.{user_id}"},
        )
        if not conversations:
            return []

        data = await self._request(
            "GET",
            "/messages",
            params={
                "select": "id,conversation_id,role,content,created_at",
                "conversation_id": f"eq.{conversation_id}",
                "order": "created_at.asc",
            },
        )
        return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

    async def insert_message(self, conversation_id: str, message: ChatMessage) -> None:
        await self._request(
            "POST",
            "/messages",
            json_body={
                "conversation_id": conversation_id,
                "role": message.role,
                "content": message.content,
            },
        )


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_supabase_client(settings: SettingsDependency) -> SupabaseClient:
    return SupabaseClient(settings=settings)
