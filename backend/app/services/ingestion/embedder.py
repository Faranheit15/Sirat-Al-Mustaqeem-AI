from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.services.ingestion.chunker import TextChunk

logger = get_logger(__name__)

_GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/{model}:batchEmbedContents"
_BATCH_SIZE = 100


async def embed_query(query: str, model: str | None = None) -> list[float]:
    """Embed a single query string using RETRIEVAL_QUERY task type."""
    settings = get_settings()
    if settings.gemini_api_key is None:
        raise RuntimeError("GEMINI_API_KEY is required for query embeddings.")

    api_key = settings.gemini_api_key.get_secret_value()
    embed_model = model or settings.gemini_embedding_model
    url = _GEMINI_EMBED_URL.format(model=embed_model)

    body = {
        "requests": [
            {
                "model": embed_model,
                "content": {"parts": [{"text": query}]},
                "taskType": "RETRIEVAL_QUERY",
            }
        ]
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=body, params={"key": api_key})
        response.raise_for_status()
    embeddings: list[dict[str, Any]] = response.json().get("embeddings", [])
    if not embeddings:
        raise RuntimeError("Gemini returned no embedding for query.")
    values: list[float] = embeddings[0].get("values", [])
    return values


async def embed_chunks(
    chunks: list[TextChunk],
    model: str | None = None,
) -> list[tuple[str, list[float], dict[str, Any]]]:
    """Embed text chunks using Gemini batchEmbedContents REST API.

    Returns list of (content, embedding_vector, metadata).
    """
    settings = get_settings()
    if settings.gemini_api_key is None:
        raise RuntimeError("GEMINI_API_KEY is required for document embeddings.")

    api_key = settings.gemini_api_key.get_secret_value()
    embed_model = model or settings.gemini_embedding_model
    url = _GEMINI_EMBED_URL.format(model=embed_model)

    results: list[tuple[str, list[float], dict[str, Any]]] = []

    async with httpx.AsyncClient(timeout=120) as client:
        for batch_start in range(0, len(chunks), _BATCH_SIZE):
            batch = chunks[batch_start : batch_start + _BATCH_SIZE]
            body = {
                "requests": [
                    {
                        "model": embed_model,
                        "content": {"parts": [{"text": chunk.content}]},
                        "taskType": "RETRIEVAL_DOCUMENT",
                    }
                    for chunk in batch
                ]
            }
            logger.debug(
                "embed_batch | model=%s batch_start=%d size=%d",
                embed_model,
                batch_start,
                len(batch),
            )
            try:
                response = await client.post(url, json=body, params={"key": api_key})
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "embed_batch_failed | batch_start=%d status=%d",
                    batch_start,
                    exc.response.status_code,
                )
                raise

            data = response.json()
            embeddings: list[dict[str, Any]] = data.get("embeddings", [])
            for chunk, emb in zip(batch, embeddings, strict=True):
                vector: list[float] = emb.get("values", [])
                meta: dict[str, Any] = {
                    **chunk.metadata,
                    "doc_type": chunk.doc_type,
                    "language": chunk.language,
                    "chunk_index": chunk.chunk_index,
                }
                results.append((chunk.content, vector, meta))

    logger.info("embed_done | total=%d", len(results))
    return results
