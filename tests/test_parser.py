from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path

from src.parsers.conversation_parser import ConversationParser


class ConversationParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = Path("tests/fixtures/sample_conversation.html").read_text(encoding="utf-8")
        self.record = ConversationParser().parse(
            html=self.html,
            url="https://chatgpt.com/c/sample-id",
            title="Sample Conversation",
            exported_at=datetime(2026, 7, 28, tzinfo=UTC),
        )

    def test_parses_ordered_messages_and_links(self) -> None:
        self.assertEqual(self.record.conversation_id, "sample-id")
        self.assertEqual(len(self.record.messages), 2)
        first, second = self.record.messages
        self.assertEqual(first.role, "user")
        self.assertEqual(second.role, "assistant")
        self.assertIsNone(first.parent_message_id)
        self.assertEqual(first.child_message_id, second.message_id)
        self.assertEqual(second.parent_message_id, first.message_id)
        self.assertIsNone(second.child_message_id)

    def test_extracts_rich_references(self) -> None:
        first, second = self.record.messages
        self.assertEqual(len(first.attachment_references), 1)
        self.assertEqual(first.attachment_references[0].original_name, "spec.pdf")
        self.assertEqual(len(second.code_references), 1)
        self.assertEqual(second.code_references[0].language, "python")
        self.assertEqual(len(second.image_references), 1)
        self.assertEqual(len(second.table_references), 1)
        self.assertEqual(second.table_references[0].headers, ["Layer", "Status"])
        self.assertEqual(len(second.citation_references), 1)
        self.assertGreater(second.word_count, 0)
        self.assertEqual(self.record.language, "en")


class ConversationParserRegressionTests(unittest.TestCase):
    def test_preserves_identical_messages_with_distinct_source_ids(self) -> None:
        html = """
        <main>
          <article data-message-author-role="user" data-message-id="first"><div class="markdown">Repeat</div></article>
          <article data-message-author-role="user" data-message-id="second"><div class="markdown">Repeat</div></article>
        </main>
        """
        record = ConversationParser().parse(
            html=html,
            url="https://chatgpt.com/c/repeated",
            title="Repeated",
            exported_at=datetime(2026, 7, 28, tzinfo=UTC),
        )
        self.assertEqual([message.message_id for message in record.messages], ["first", "second"])

    def test_detects_opaque_attachment_links_from_semantic_attributes(self) -> None:
        html = """
        <main><article data-message-author-role="user" data-message-id="one">
          <div class="markdown"><a href="/backend-api/files/opaque" data-testid="file-attachment">Download</a></div>
        </article></main>
        """
        record = ConversationParser().parse(
            html=html,
            url="https://chatgpt.com/c/opaque",
            title="Opaque",
            exported_at=datetime(2026, 7, 28, tzinfo=UTC),
        )
        self.assertEqual(len(record.messages[0].attachment_references), 1)
        self.assertEqual(record.messages[0].attachment_references[0].source_url, "https://chatgpt.com/backend-api/files/opaque")

if __name__ == "__main__":
    unittest.main()
