from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import Settings
from app.core.logging import get_logger
from app.services.ingestion.embedder import embed_query
from app.services.supabase import SupabaseClient

logger = get_logger(__name__)


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    document_title: str
    chunk_index: int
    content: str
    doc_type: str
    similarity: float
    language: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def source_label(self) -> str:
        """Human-readable citation reference for context block formatting."""
        if self.doc_type == "quran":
            start = self.metadata.get("ayah_start")
            end = self.metadata.get("ayah_end")
            if start and end and start != end:
                ref = f"Ayah {start}–{end}"
            elif start:
                ref = f"Ayah {start}"
            else:
                ref = "Quran"
            return f"{self.document_title} | {ref}"
        if self.doc_type == "hadith":
            num = self.metadata.get("hadith_number")
            if num:
                return f"{self.document_title} | Hadith {num}"
        return self.document_title


async def semantic_search(
    query: str,
    supabase: SupabaseClient,
    settings: Settings,
    top_k: int | None = None,
    threshold: float | None = None,
) -> list[SearchResult]:
    """Embed query and return ranked chunks from the knowledge base.

    Returns an empty list if no documents are ingested or the embedding call
    fails — callers can always proceed without RAG context in that case.
    """
    resolved_top_k = top_k if top_k is not None else settings.rag_top_k
    resolved_threshold = threshold if threshold is not None else settings.rag_threshold

    logger.info(
        "rag_search | query_len=%d top_k=%d threshold=%.2f",
        len(query),
        resolved_top_k,
        resolved_threshold,
    )

    try:
        query_vector = await embed_query(query)
    except Exception as exc:
        logger.warning("rag_embed_failed | error=%s", exc)
        return []

    try:
        rows = await supabase.match_chunks(
            query_embedding=query_vector,
            match_count=resolved_top_k,
            match_threshold=resolved_threshold,
        )
    except Exception as exc:
        logger.warning("rag_match_failed | error=%s", exc)
        return []

    results = [
        SearchResult(
            chunk_id=str(row["chunk_id"]),
            document_id=str(row["document_id"]),
            document_title=str(row["document_title"]),
            chunk_index=int(row["chunk_index"]),
            content=str(row["content"]),
            doc_type=str(row.get("doc_type") or "general"),
            language=row.get("language"),
            metadata=row.get("metadata") or {},
            similarity=float(row["similarity"]),
        )
        for row in rows
    ]

    logger.info("rag_search_done | results=%d", len(results))
    return results


def build_context_block(results: list[SearchResult]) -> str:
    """Format search results into the context section injected into the system prompt."""
    if not results:
        return ""
    lines = ["CONTEXT FROM KNOWLEDGE BASE:"]
    for r in results:
        lines += ["---", f"Source: {r.source_label()}", f"Content: {r.content}"]
    lines += [
        "---",
        "",
        "Based on the above context, answer the user's question.",
        "Always cite sources using the format shown above.",
        "If the context doesn't contain relevant information, say so clearly.",
    ]
    return "\n".join(lines)
