"""RAG-ready logical chunk and mapping generation."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from src.models.archive import (
    ChunkMapData,
    ChunkMapEntry,
    RagChunk,
    RagChunksData,
    RagDocumentEntry,
    RagDocumentsData,
    RagKeywordsData,
)
from src.models.conversation import ConversationRecord
from src.models.archive import SearchIndexData
from src.utils.text import word_count


class RagBuilder:
    """Split conversations on message boundaries into portable RAG structures."""

    def __init__(self, target_characters: int = 4000) -> None:
        self.target_characters = target_characters

    def build(
        self,
        conversation: ConversationRecord,
        search_index: SearchIndexData,
    ) -> tuple[RagChunksData, RagDocumentsData, RagKeywordsData, ChunkMapData]:
        """Build all frozen RAG documents."""
        chunks: list[RagChunk] = []
        current_messages: list[str] = []
        current_parts: list[str] = []
        current_length = 0

        def flush() -> None:
            nonlocal current_messages, current_parts, current_length
            if not current_messages:
                return
            sequence_number = len(chunks) + 1
            text = "\n\n".join(current_parts)
            chunk_id = str(uuid5(NAMESPACE_URL, f"{conversation.conversation_id}:chunk:{sequence_number}:{','.join(current_messages)}"))
            chunks.append(
                RagChunk(
                    chunk_id=chunk_id,
                    sequence_number=sequence_number,
                    message_ids=list(current_messages),
                    text=text,
                    character_count=len(text),
                    word_count=word_count(text),
                    metadata={
                        "conversationId": conversation.conversation_id,
                        "title": conversation.title,
                        "sourceUrl": conversation.url,
                    },
                )
            )
            current_messages = []
            current_parts = []
            current_length = 0

        for message in conversation.messages:
            rendered = f"{message.role.title()}\n\n{message.markdown or message.plain_text}".strip()
            projected = current_length + len(rendered) + (2 if current_parts else 0)
            if current_parts and projected > self.target_characters:
                flush()
            current_messages.append(message.message_id)
            current_parts.append(rendered)
            current_length += len(rendered) + (2 if len(current_parts) > 1 else 0)
        flush()

        mappings = [
            ChunkMapEntry(message_id=message_id, chunk_id=chunk.chunk_id)
            for chunk in chunks
            for message_id in chunk.message_ids
        ]
        document_id = str(uuid5(NAMESPACE_URL, f"{conversation.conversation_id}:document"))
        documents = RagDocumentsData(
            documents=[
                RagDocumentEntry(
                    document_id=document_id,
                    conversation_id=conversation.conversation_id,
                    title=conversation.title,
                    source_url=conversation.url,
                    chunk_ids=[chunk.chunk_id for chunk in chunks],
                    metadata={
                        "messageCount": len(conversation.messages),
                        "language": conversation.language,
                    },
                )
            ]
        )
        return (
            RagChunksData(conversation_id=conversation.conversation_id, chunks=chunks),
            documents,
            RagKeywordsData(
                conversation_id=conversation.conversation_id,
                keywords=search_index.keywords,
                topics=search_index.topics,
            ),
            ChunkMapData(conversation_id=conversation.conversation_id, mappings=mappings),
        )
