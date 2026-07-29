"""Deterministic local summary and topic generation."""

from __future__ import annotations

import re

from src.models.archive import SummaryData
from src.models.conversation import ConversationRecord
from src.utils.text import (
    deduplicate,
    extract_file_mentions,
    extract_urls,
    keyword_frequencies,
    split_sentences,
)

_TECHNOLOGY_NAMES = (
    "Python", "Playwright", "CustomTkinter", "Chrome", "Chromium", "Docker", "Cloudflare",
    "FastAPI", "Flask", "SQLite", "GitHub Actions", "Nuitka", "RAG", "LLM", "JSON", "Markdown",
    "BeautifulSoup", "Pillow", "Pydantic", "Tenacity", "JavaScript", "TypeScript", "HTML", "CSS",
)
_LIBRARY_NAMES = (
    "customtkinter", "playwright", "beautifulsoup4", "bs4", "markdownify", "pillow", "pydantic", "tenacity",
)
_DECISION_MARKERS = re.compile(
    r"\b(decided|decision|selected|chosen|will use|must use|official|frozen|agreed|approved)\b|"
    r"(সিদ্ধান্ত|নির্ধারণ|ব্যবহার করা হবে|চূড়ান্ত|ফ্রোজেন)",
    re.IGNORECASE,
)
_TODO_MARKERS = re.compile(
    r"\b(todo|to-do|action item|need to|must implement|remaining|next step)\b|"
    r"(করতে হবে|বাকি|পরবর্তী ধাপ|বাস্তবায়ন)",
    re.IGNORECASE,
)


class SummaryBuilder:
    """Generate reproducible, dependency-free archive summaries."""

    def build(self, conversation: ConversationRecord) -> SummaryData:
        """Build extractive summaries and structured mentions."""
        message_texts = [message.plain_text for message in conversation.messages if message.plain_text]
        combined = "\n".join(message_texts)
        sentences = split_sentences(combined)
        frequencies = keyword_frequencies(message_texts, limit=40)
        keywords = [term for term, _ in frequencies[:25]]
        topics = [term for term, count in frequencies[:12] if count >= 2] or keywords[:8]
        ranked_sentences = self._rank_sentences(sentences, dict(frequencies))
        short_summary = self._join_limited(ranked_sentences[:3], 600)
        long_summary = self._join_limited(ranked_sentences[:12], 3000)
        if not short_summary:
            short_summary = f"Conversation '{conversation.title}' contains {len(conversation.messages)} messages."
        if not long_summary:
            long_summary = short_summary

        decisions = deduplicate(sentence for sentence in sentences if _DECISION_MARKERS.search(sentence))[:30]
        todos = deduplicate(sentence for sentence in sentences if _TODO_MARKERS.search(sentence))[:30]
        technologies = [name for name in _TECHNOLOGY_NAMES if re.search(rf"\b{re.escape(name)}\b", combined, re.IGNORECASE)]
        libraries = [name for name in _LIBRARY_NAMES if re.search(rf"\b{re.escape(name)}\b", combined, re.IGNORECASE)]
        return SummaryData(
            short_summary=short_summary,
            long_summary=long_summary,
            main_topics=topics,
            keywords=keywords,
            important_decisions=decisions,
            todo_list=todos,
            mentioned_technologies=technologies,
            mentioned_libraries=libraries,
            mentioned_urls=extract_urls(combined),
            mentioned_files=extract_file_mentions(combined),
        )

    @staticmethod
    def _rank_sentences(sentences: list[str], frequencies: dict[str, int]) -> list[str]:
        scored: list[tuple[float, int, str]] = []
        for index, sentence in enumerate(sentences):
            normalized_words = re.findall(r"[\w'’-]+", sentence.lower())
            if not normalized_words:
                continue
            score = sum(frequencies.get(word, 0) for word in normalized_words) / max(len(normalized_words), 1)
            if _DECISION_MARKERS.search(sentence):
                score += 2.0
            if 30 <= len(sentence) <= 320:
                score += 0.5
            scored.append((score, index, sentence))
        best = sorted(scored, key=lambda item: (-item[0], item[1]))[:20]
        selected = sorted(best, key=lambda item: item[1])
        return [sentence for _, _, sentence in selected]

    @staticmethod
    def _join_limited(sentences: list[str], limit: int) -> str:
        output: list[str] = []
        length = 0
        for sentence in sentences:
            additional = len(sentence) + (1 if output else 0)
            if output and length + additional > limit:
                break
            output.append(sentence)
            length += additional
        return " ".join(output)
