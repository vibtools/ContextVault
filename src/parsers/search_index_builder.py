"""Conversation keyword, entity, and message index generation."""

from __future__ import annotations

import re
from collections import defaultdict

from src.models.archive import SearchIndexData, SearchMessageMapping
from src.models.conversation import ConversationRecord
from src.utils.text import keyword_frequencies

_ENTITY_PATTERN = re.compile(r"\b(?:[A-Z][A-Za-z0-9+#.-]{2,})(?:\s+[A-Z][A-Za-z0-9+#.-]{2,}){0,3}\b")


class SearchIndexBuilder:
    """Create deterministic local search structures for an archive."""

    def build(self, conversation: ConversationRecord) -> SearchIndexData:
        """Generate terms and mappings without external search dependencies."""
        texts = [message.plain_text for message in conversation.messages]
        frequencies = keyword_frequencies(texts, limit=100)
        keywords = [term for term, _ in frequencies[:50]]
        topics = [term for term, count in frequencies[:20] if count >= 2]
        term_messages: dict[str, list[str]] = defaultdict(list)
        entities: dict[str, list[str]] = defaultdict(list)

        for message in conversation.messages:
            lowered = message.plain_text.lower()
            for term in keywords:
                if term in lowered:
                    term_messages[term].append(message.message_id)
            for entity in _ENTITY_PATTERN.findall(message.plain_text):
                if entity.lower() in {term.lower() for term in keywords[:5]}:
                    continue
                if message.message_id not in entities[entity]:
                    entities[entity].append(message.message_id)

        mappings = [
            SearchMessageMapping(term=term, message_ids=term_messages.get(term, []))
            for term in keywords
        ]
        return SearchIndexData(
            keywords=keywords,
            topics=topics,
            important_terms=keywords[:20],
            entity_mapping=dict(sorted(entities.items(), key=lambda item: item[0].lower())),
            message_mapping=mappings,
            conversation_mapping={conversation.conversation_id: [message.message_id for message in conversation.messages]},
        )
