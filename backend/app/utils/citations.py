from __future__ import annotations

import re
from dataclasses import dataclass

# Matches any bracketed expression between 5 and 150 chars with no nested brackets.
_BRACKET_RE = re.compile(r"\[([^\[\]\n]{5,150})\]")

_QURAN_RE = re.compile(r"^Quran\s+\d+:\d+", re.IGNORECASE)

_HADITH_PREFIXES = frozenset(
    {
        "sahih bukhari",
        "sahih muslim",
        "abu dawud",
        "sunan abu dawud",
        "jami tirmidhi",
        "sunan tirmidhi",
        "sunan al-nasai",
        "sunan nasai",
        "sunan ibn majah",
        "ibn majah",
        "musnad ahmad",
        "riyad al-salihin",
        "muwatta",
        "al-muwatta",
    }
)


@dataclass
class Citation:
    type: str  # "quran" | "hadith" | "scholarly"
    reference: str
    source_doc_id: str | None = None


def _classify(text: str) -> str:
    stripped = text.strip()
    if _QURAN_RE.match(stripped):
        return "quran"
    lower = stripped.lower()
    for prefix in _HADITH_PREFIXES:
        if lower.startswith(prefix):
            return "hadith"
    # Treat as scholarly if it contains a comma (Author, Book pattern).
    if "," in stripped:
        return "scholarly"
    return "other"


def extract_citations(text: str) -> list[Citation]:
    """Parse citation brackets from LLM response text.

    Handles:
      [Quran 2:255]
      [Sahih Bukhari, 6018]  or  [Sahih Bukhari 6018]
      [Ibn Kathir, Tafsir al-Quran, Vol 1]
    """
    citations: list[Citation] = []
    seen: set[str] = set()
    for m in _BRACKET_RE.finditer(text):
        raw = m.group(1).strip()
        category = _classify(raw)
        if category == "other":
            continue
        if raw not in seen:
            citations.append(Citation(type=category, reference=raw))
            seen.add(raw)
    return citations
