from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    doc_type: str
    language: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


_QURAN_PATTERNS = [
    re.compile(r"\(\d+\)"),
    re.compile(r"بِسْمِ اللَّهِ"),
    re.compile(r"سُورَة"),
]
_HADITH_PATTERNS = [
    re.compile(r"حَدَّثَنَا|حَدَّثَنِي"),
    re.compile(r"قَالَ رَسُولُ اللَّهِ"),
    re.compile(r"Narrated\b", re.IGNORECASE),
    re.compile(r"حدثنا"),
]


def _detect_doc_type(text: str) -> str:
    sample = text[:3000]
    for pat in _QURAN_PATTERNS:
        if pat.search(sample):
            return "quran"
    for pat in _HADITH_PATTERNS:
        if pat.search(sample):
            return "hadith"
    return "general"


def _chunk_quran(text: str, language: str | None, chunk_size: int) -> list[TextChunk]:
    ayah_split = re.compile(r"(?=\(\d+\))")
    parts = [p.strip() for p in ayah_split.split(text) if p.strip()]

    chunks: list[TextChunk] = []
    current_parts: list[str] = []
    current_tokens = 0
    ayah_start: int | None = None
    ayah_end: int | None = None
    chunk_index = 0

    def _flush() -> None:
        nonlocal chunk_index, current_parts, current_tokens, ayah_start, ayah_end
        if current_parts:
            chunks.append(
                TextChunk(
                    content=" ".join(current_parts),
                    chunk_index=chunk_index,
                    doc_type="quran",
                    language=language,
                    metadata={"ayah_start": ayah_start, "ayah_end": ayah_end},
                )
            )
            chunk_index += 1
            current_parts = []
            current_tokens = 0
            ayah_start = None
            ayah_end = None

    for part in parts:
        m = re.match(r"\((\d+)\)", part)
        num = int(m.group(1)) if m else None
        tokens = len(part.split())
        if current_tokens + tokens > chunk_size and current_parts:
            _flush()
        current_parts.append(part)
        current_tokens += tokens
        if num is not None:
            if ayah_start is None:
                ayah_start = num
            ayah_end = num

    _flush()
    return chunks


def _chunk_hadith(text: str, language: str | None) -> list[TextChunk]:
    split_pat = re.compile(
        r"(?=(?:حديث|Hadith)\s*\d+)",
        re.IGNORECASE,
    )
    parts = [p.strip() for p in split_pat.split(text) if p.strip()]
    if not parts:
        parts = [text.strip()]

    chunks: list[TextChunk] = []
    for i, part in enumerate(parts):
        m = re.match(r"(?:حديث|Hadith)\s*(\d+)", part, re.IGNORECASE)
        hadith_num = int(m.group(1)) if m else None
        chunks.append(
            TextChunk(
                content=part,
                chunk_index=i,
                doc_type="hadith",
                language=language,
                metadata={"hadith_number": hadith_num},
            )
        )
    return chunks


def _chunk_general(
    text: str, language: str | None, chunk_size: int, overlap: int
) -> list[TextChunk]:
    words = text.split()
    chunks: list[TextChunk] = []
    start = 0
    chunk_index = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(
            TextChunk(
                content=" ".join(words[start:end]),
                chunk_index=chunk_index,
                doc_type="general",
                language=language,
                metadata={},
            )
        )
        chunk_index += 1
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def chunk_document(
    text: str,
    document_id: str,
    language: str | None,
    chunk_size: int = 500,
    overlap: int = 50,
    doc_type: str | None = None,
) -> list[TextChunk]:
    if not text.strip():
        return []

    resolved_type = doc_type or _detect_doc_type(text)

    if resolved_type == "quran":
        chunks = _chunk_quran(text, language, chunk_size)
    elif resolved_type == "hadith":
        chunks = _chunk_hadith(text, language)
    else:
        chunks = _chunk_general(text, language, chunk_size, overlap)

    for chunk in chunks:
        chunk.metadata["document_id"] = document_id

    return chunks
