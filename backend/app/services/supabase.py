from datetime import UTC, datetime
from typing import Annotated, Any, cast
from uuid import uuid4

import httpx
from fastapi import Depends

from app.config import Settings, get_settings
from app.core.logging import get_logger

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

        last_exc: Exception | None = None
        for attempt in range(2):  # retry once on remote disconnection
            try:
                async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
                    response = await client.request(
                        method,
                        url,
                        params=params,
                        json=json_body,
                        headers=headers,
                    )
                    response.raise_for_status()
                if response.status_code == 204 or not response.content:
                    return None
                return response.json()
            except httpx.RemoteProtocolError as exc:
                last_exc = exc
                logger.warning(
                    "supabase_disconnected | method=%s path=%s attempt=%d retrying",
                    method,
                    path,
                    attempt + 1,
                )
                continue
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "supabase_error | method=%s path=%s status=%s body=%s",
                    method,
                    path,
                    exc.response.status_code,
                    exc.response.text,
                )
                raise
        raise last_exc or RuntimeError(f"supabase_request failed: {method} {path}")

    async def list_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/conversations",
            params={
                "select": "id,user_id,title,created_at,updated_at",
                "user_id": f"eq.{user_id}",
                "order": "updated_at.desc",
                "limit": str(limit),
                "offset": str(offset),
            },
        )
        return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

    async def get_conversation(self, user_id: str, conversation_id: str) -> dict[str, Any] | None:
        data = await self._request(
            "GET",
            "/conversations",
            params={
                "select": "id,user_id,title,created_at,updated_at",
                "id": f"eq.{conversation_id}",
                "user_id": f"eq.{user_id}",
                "limit": "1",
            },
        )
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return cast(dict[str, Any], data[0])
        return None

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
                "select": "id,conversation_id,role,content,citations,created_at",
                "conversation_id": f"eq.{conversation_id}",
                "order": "created_at.asc",
            },
        )
        return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

    async def insert_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        body: dict[str, Any] = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        }
        if citations is not None:
            body["citations"] = citations

        data = await self._request(
            "POST",
            "/messages",
            json_body=body,
            prefer="return=representation",
        )
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return cast(dict[str, Any], data[0])
        return None

    # --- Storage ---

    def _storage_headers(self, content_type: str) -> dict[str, str]:
        if self.settings.supabase_service_role_key is None:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required.")
        key = self.settings.supabase_service_role_key.get_secret_value()
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": content_type,
            "x-upsert": "true",
            "cache-control": "max-age=3600",
        }

    async def upload_file(
        self,
        path: str,
        content: bytes,
        content_type: str,
    ) -> str:
        bucket = self.settings.supabase_storage_bucket
        url = f"{self.settings.supabase_storage_url}/object/{bucket}/{path}"
        headers = self._storage_headers(content_type)
        logger.debug("storage_upload | bucket=%s path=%s size=%d", bucket, path, len(content))
        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            response = await client.post(url, content=content, headers=headers)
            if not response.is_success:
                logger.error(
                    "storage_upload_failed | status=%d body=%s",
                    response.status_code,
                    response.text,
                )
            response.raise_for_status()
        return path

    async def delete_file(self, path: str) -> None:
        bucket = self.settings.supabase_storage_bucket
        url = f"{self.settings.supabase_storage_url}/object/{bucket}"
        if self.settings.supabase_service_role_key is None:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required.")
        key = self.settings.supabase_service_role_key.get_secret_value()
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        logger.debug("storage_delete | bucket=%s path=%s", bucket, path)
        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            response = await client.delete(f"{url}/{path}", headers=headers)
            if response.status_code not in (200, 204, 404):
                response.raise_for_status()

    # --- Documents ---

    async def create_document(
        self,
        title: str,
        file_type: str,
        file_size: int,
        file_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        body: dict[str, Any] = {
            "id": str(uuid4()),
            "title": title,
            "file_type": file_type,
            "file_size": file_size,
            "file_path": file_path,
            "status": "pending",
            "chunk_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        if metadata is not None:
            body["metadata"] = metadata
        data = await self._request(
            "POST", "/documents", json_body=body, prefer="return=representation"
        )
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return cast(dict[str, Any], data[0])
        raise RuntimeError("Failed to create document record.")

    async def list_documents(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/documents",
            params={
                "select": (
                    "id,title,file_type,file_size,file_path,language,"
                    "page_count,is_ocr,status,chunk_count,created_at,updated_at"
                ),
                "order": "created_at.desc",
                "limit": str(limit),
                "offset": str(offset),
            },
        )
        return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

    async def count_documents(self) -> int:
        data = await self._request(
            "GET",
            "/documents",
            params={"select": "id", "limit": "1000"},
        )
        return len(data) if isinstance(data, list) else 0

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        data = await self._request(
            "GET",
            "/documents",
            params={
                "select": (
                    "id,title,file_type,file_size,file_path,language,"
                    "page_count,is_ocr,status,chunk_count,created_at,updated_at,metadata"
                ),
                "id": f"eq.{document_id}",
                "limit": "1",
            },
        )
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return cast(dict[str, Any], data[0])
        return None

    async def update_document(self, document_id: str, fields: dict[str, Any]) -> None:
        fields["updated_at"] = datetime.now(UTC).isoformat()
        await self._request(
            "PATCH",
            "/documents",
            params={"id": f"eq.{document_id}"},
            json_body=fields,
        )

    async def delete_document(self, document_id: str) -> None:
        await self._request("DELETE", "/documents", params={"id": f"eq.{document_id}"})

    # --- Document chunks ---

    async def insert_chunks(self, chunks: list[dict[str, Any]]) -> None:
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            await self._request(
                "POST",
                "/document_chunks",
                json_body=chunks[i : i + batch_size],
                prefer="return=minimal",
            )

    async def delete_chunks(self, document_id: str) -> None:
        await self._request(
            "DELETE",
            "/document_chunks",
            params={"document_id": f"eq.{document_id}"},
        )

    # --- Ingestion jobs ---

    async def create_ingestion_job(self, document_id: str) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        body: dict[str, Any] = {
            "id": str(uuid4()),
            "document_id": document_id,
            "status": "pending",
            "progress": 0,
            "started_at": now,
            "created_at": now,
        }
        data = await self._request(
            "POST", "/ingestion_jobs", json_body=body, prefer="return=representation"
        )
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return cast(dict[str, Any], data[0])
        raise RuntimeError("Failed to create ingestion job.")

    async def update_ingestion_job(
        self,
        job_id: str,
        status: str,
        progress: int,
        error_log: str | None = None,
        completed_at: str | None = None,
    ) -> None:
        fields: dict[str, Any] = {"status": status, "progress": progress}
        if error_log is not None:
            fields["error_log"] = error_log
        if completed_at is not None:
            fields["completed_at"] = completed_at
        await self._request(
            "PATCH",
            "/ingestion_jobs",
            params={"id": f"eq.{job_id}"},
            json_body=fields,
        )

    async def list_ingestion_jobs(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/ingestion_jobs",
            params={
                "select": (
                    "id,document_id,status,progress,error_log,started_at,completed_at,created_at"
                ),
                "order": "created_at.desc",
                "limit": str(limit),
                "offset": str(offset),
            },
        )
        return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

    async def match_chunks(
        self,
        query_embedding: list[float],
        match_count: int = 5,
        match_threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "POST",
            "/rpc/match_chunks",
            json_body={
                "query_embedding": query_embedding,
                "match_count": match_count,
                "match_threshold": match_threshold,
            },
        )
        if not isinstance(data, list):
            return []
        return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

    async def get_ingestion_job(self, job_id: str) -> dict[str, Any] | None:
        data = await self._request(
            "GET",
            "/ingestion_jobs",
            params={
                "select": (
                    "id,document_id,status,progress,error_log,started_at,completed_at,created_at"
                ),
                "id": f"eq.{job_id}",
                "limit": "1",
            },
        )
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return cast(dict[str, Any], data[0])
        return None

    async def list_stuck_ingestion_jobs(self) -> list[dict[str, Any]]:
        """Return jobs whose status indicates they were interrupted mid-run."""
        _STUCK = ("extracting", "chunking", "embedding", "storing")
        data = await self._request(
            "GET",
            "/ingestion_jobs",
            params={
                "select": "id,document_id,status,progress,started_at,created_at",
                "status": f"in.({','.join(_STUCK)})",
                "order": "created_at.asc",
            },
        )
        return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

    async def get_ingestion_job_by_document(self, document_id: str) -> dict[str, Any] | None:
        data = await self._request(
            "GET",
            "/ingestion_jobs",
            params={
                "select": (
                    "id,document_id,status,progress,error_log,started_at,completed_at,created_at"
                ),
                "document_id": f"eq.{document_id}",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return cast(dict[str, Any], data[0])
        return None

    # --- DB health ---

    async def check_db(self) -> tuple[bool, list[str], str | None]:
        """Returns (is_healthy, table_names, error_message)."""
        try:
            if (
                self.settings.supabase_service_role_key is None
                or self.settings.supabase_url is None
            ):
                return False, [], "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not configured."
            key = self.settings.supabase_service_role_key.get_secret_value()
            headers = {
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    self.settings.supabase_rest_url + "/",
                    headers=headers,
                )
                response.raise_for_status()
                spec = response.json()
            tables: list[str] = []
            if isinstance(spec, dict):
                definitions = spec.get("definitions") or spec.get("paths") or {}
                if isinstance(definitions, dict):
                    tables = [k for k in definitions if not k.startswith("/")]
                    if not tables:
                        # paths keys start with "/" — strip leading slash
                        tables = [k.lstrip("/") for k in definitions]
            return True, sorted(tables), None
        except Exception as exc:
            return False, [], str(exc)


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_supabase_client(settings: SettingsDependency) -> SupabaseClient:
    return SupabaseClient(settings=settings)
