"""Deterministic text statistics and extraction helpers."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

_WORD_PATTERN = re.compile(r"[\w][\w'’-]*", re.UNICODE)
_URL_PATTERN = re.compile(r"https?://[^\s<>()\[\]{}\"']+")
_FILE_PATTERN = re.compile(r"\b[\w.-]+\.(?:py|js|ts|html|css|json|ya?ml|md|txt|csv|pdf|docx|xlsx|zip)\b", re.IGNORECASE)
_SENTENCE_PATTERN = re.compile(r"(?<=[.!?।])\s+")
_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "into", "your", "you", "are", "was", "were",
    "will", "have", "has", "had", "not", "but", "can", "could", "should", "would", "about", "there",
    "their", "then", "than", "when", "where", "what", "which", "who", "why", "how", "also", "only",
    "একটি", "এই", "এবং", "করে", "করা", "হবে", "থেকে", "যদি", "জন্য", "সকল", "কোনো", "ব্যবহার",
    "করতে", "যাবে", "নয়", "না", "এর", "যে", "তা", "থাকবে", "হয়", "হলো", "হবে।",
}


def words(text: str) -> list[str]:
    """Extract Unicode words from text."""
    return _WORD_PATTERN.findall(text)


def word_count(text: str) -> int:
    """Return deterministic word count."""
    return len(words(text))


def estimated_tokens(text: str) -> int:
    """Estimate tokens without introducing a tokenizer dependency."""
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def split_sentences(text: str) -> list[str]:
    """Split readable text into sentences while preserving order."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    return [part.strip() for part in _SENTENCE_PATTERN.split(normalized) if part.strip()]


def extract_urls(text: str) -> list[str]:
    """Return unique URLs in first-seen order."""
    return deduplicate(_URL_PATTERN.findall(text))


def extract_file_mentions(text: str) -> list[str]:
    """Return unique file-name mentions in first-seen order."""
    return deduplicate(_FILE_PATTERN.findall(text))


def keyword_frequencies(texts: Iterable[str], *, limit: int = 40) -> list[tuple[str, int]]:
    """Return normalized keyword frequencies with common stopwords removed."""
    counter: Counter[str] = Counter()
    for text in texts:
        for value in words(text.lower()):
            normalized = value.strip("_'’-.")
            if len(normalized) < 3 or normalized.isdigit() or normalized in _STOPWORDS:
                continue
            counter[normalized] += 1
    return counter.most_common(limit)


def deduplicate(values: Iterable[str]) -> list[str]:
    """Deduplicate strings while preserving first-seen order."""
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output
