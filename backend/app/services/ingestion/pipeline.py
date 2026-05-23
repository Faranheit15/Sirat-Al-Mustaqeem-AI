from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.config import Settings
from app.core.logging import get_logger
from app.services.ingestion.chunker import chunk_document
from app.services.ingestion.embedder import embed_chunks
from app.services.ingestion.extractor import extract_document
from app.services.supabase import SupabaseClient

logger = get_logger(__name__)


class IngestionPipeline:
    def __init__(self, supabase: SupabaseClient, settings: Settings) -> None:
        self.supabase = supabase
        self.settings = settings

    async def run(
        self,
        document_id: str,
        job_id: str,
        file_bytes: bytes,
        file_type: str,
    ) -> None:
        logger.info(
            "ingestion_start | document_id=%s job_id=%s file_type=%s",
            document_id,
            job_id,
            file_type,
        )
        try:
            await self._extract(document_id, job_id, file_bytes, file_type)
        except Exception as exc:
            logger.error(
                "ingestion_failed | document_id=%s job_id=%s error=%s",
                document_id,
                job_id,
                exc,
            )
            await self.supabase.update_ingestion_job(
                job_id,
                status="failed",
                progress=0,
                error_log=str(exc),
                completed_at=datetime.now(UTC).isoformat(),
            )
            await self.supabase.update_document(document_id, {"status": "failed"})

    async def _extract(
        self, document_id: str, job_id: str, file_bytes: bytes, file_type: str
    ) -> None:
        await self.supabase.update_ingestion_job(job_id, status="extracting", progress=10)
        extracted = extract_document(file_bytes, file_type)
        logger.info(
            "ingestion_extracted | document_id=%s pages=%d is_ocr=%s chars=%d",
            document_id,
            extracted.page_count,
            extracted.is_ocr,
            len(extracted.text),
        )
        await self.supabase.update_document(
            document_id,
            {
                "status": "processing",
                "language": extracted.language_detected,
                "page_count": extracted.page_count,
                "is_ocr": extracted.is_ocr,
            },
        )
        await self._chunk(document_id, job_id, extracted.text, extracted.language_detected)

    async def _chunk(
        self,
        document_id: str,
        job_id: str,
        text: str,
        language: str | None,
    ) -> None:
        await self.supabase.update_ingestion_job(job_id, status="chunking", progress=30)
        chunks = chunk_document(
            text=text,
            document_id=document_id,
            language=language,
            chunk_size=self.settings.ingestion_chunk_size,
            overlap=self.settings.ingestion_chunk_overlap,
        )
        logger.info("ingestion_chunked | document_id=%s chunks=%d", document_id, len(chunks))
        await self._embed(document_id, job_id, chunks)

    async def _embed(self, document_id: str, job_id: str, chunks: Any) -> None:
        await self.supabase.update_ingestion_job(job_id, status="embedding", progress=50)
        embedded = await embed_chunks(chunks)
        logger.info("ingestion_embedded | document_id=%s count=%d", document_id, len(embedded))
        await self._store(document_id, job_id, embedded)

    async def _store(
        self,
        document_id: str,
        job_id: str,
        embedded: list[tuple[str, list[float], dict[str, Any]]],
    ) -> None:
        await self.supabase.update_ingestion_job(job_id, status="storing", progress=80)
        rows: list[dict[str, Any]] = [
            {
                "id": str(uuid4()),
                "document_id": document_id,
                "chunk_index": meta.get("chunk_index", i),
                "content": content,
                "embedding": vector,
                "doc_type": meta.get("doc_type", "general"),
                "language": meta.get("language"),
                "metadata": {
                    k: v
                    for k, v in meta.items()
                    if k not in ("chunk_index", "doc_type", "language", "document_id")
                },
            }
            for i, (content, vector, meta) in enumerate(embedded)
        ]
        await self.supabase.insert_chunks(rows)
        await self.supabase.update_document(document_id, {"chunk_count": len(rows)})
        await self.supabase.update_ingestion_job(
            job_id,
            status="completed",
            progress=100,
            completed_at=datetime.now(UTC).isoformat(),
        )
        await self.supabase.update_document(document_id, {"status": "completed"})
        logger.info(
            "ingestion_done | document_id=%s job_id=%s chunks=%d",
            document_id,
            job_id,
            len(rows),
        )
