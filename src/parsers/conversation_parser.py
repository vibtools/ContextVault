"""Resilient HTML-to-domain conversation parser."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from uuid import NAMESPACE_URL, uuid5

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

from src.config.constants import SUPPORTED_ASSET_EXTENSIONS
from src.models.conversation import (
    AttachmentReference,
    CitationReference,
    CodeReference,
    ConversationMessage,
    ConversationRecord,
    ImageReference,
    TableReference,
)
from src.utils.text import estimated_tokens, word_count

LOGGER = logging.getLogger(__name__)
_LANGUAGE_CLASS_PATTERN = re.compile(r"(?:language|lang)-([A-Za-z0-9_+#.-]+)")
_CONVERSATION_ID_PATTERN = re.compile(r"/(?:c|conversation)/([^/?#]+)")


class ConversationParser:
    """Convert fully loaded conversation HTML into validated domain models."""

    MESSAGE_SELECTORS = (
        "[data-message-author-role]",
        "[data-testid^='conversation-turn']",
        "main article",
    )

    def parse(
        self,
        *,
        html: str,
        url: str,
        title: str,
        platform_name: str = "ChatGPT",
        exported_at: datetime,
    ) -> ConversationRecord:
        """Parse a complete conversation document while preserving rich content."""
        soup = BeautifulSoup(html, "html.parser")
        for unwanted in soup.select("script, style, noscript"):
            unwanted.decompose()

        conversation_id = self._conversation_id(url, title)
        message_nodes = self._find_message_nodes(soup)
        messages: list[ConversationMessage] = []
        seen_message_ids: set[str] = set()

        for sequence_number, node in enumerate(message_nodes, start=1):
            message = self._parse_message(
                node=node,
                sequence_number=sequence_number,
                conversation_id=conversation_id,
                base_url=url,
            )
            if message.message_id in seen_message_ids:
                LOGGER.debug("Duplicate message ID skipped at sequence %s: %s", sequence_number, message.message_id)
                continue
            seen_message_ids.add(message.message_id)
            messages.append(message)

        self._resequence_and_link(messages)
        combined_text = "\n".join(message.plain_text for message in messages)
        return ConversationRecord(
            conversation_id=conversation_id,
            title=title.strip() or "Untitled Conversation",
            url=url,
            platform_name=platform_name,
            created_at=self._conversation_created_at(soup),
            exported_at=exported_at,
            language=self._detect_language(combined_text),
            messages=messages,
        )

    def _find_message_nodes(self, soup: BeautifulSoup) -> list[Tag]:
        for selector in self.MESSAGE_SELECTORS:
            candidates = [node for node in soup.select(selector) if isinstance(node, Tag)]
            if not candidates:
                continue
            if selector == "[data-message-author-role]":
                return self._remove_nested_candidates(candidates, "data-message-author-role")
            return self._remove_nested_candidates(candidates, None)
        return []

    @staticmethod
    def _remove_nested_candidates(candidates: list[Tag], attribute: str | None) -> list[Tag]:
        candidate_ids = {id(item) for item in candidates}
        output: list[Tag] = []
        for candidate in candidates:
            parent = candidate.parent
            nested = False
            while isinstance(parent, Tag):
                if id(parent) in candidate_ids:
                    if attribute is None or parent.get(attribute) == candidate.get(attribute):
                        nested = True
                        break
                parent = parent.parent
            if not nested:
                output.append(candidate)
        return output

    def _parse_message(
        self,
        *,
        node: Tag,
        sequence_number: int,
        conversation_id: str,
        base_url: str,
    ) -> ConversationMessage:
        role = self._extract_role(node)
        content_node = self._content_node(node)
        html = content_node.decode_contents(formatter="html").strip()
        plain_text = content_node.get_text("\n", strip=True)
        markdown = markdownify(html, heading_style="ATX", bullets="-").strip() if html else plain_text
        source_id = (
            node.get("data-message-id")
            or node.get("data-testid")
            or node.get("id")
            or str(uuid5(NAMESPACE_URL, f"{conversation_id}:{sequence_number}:{role}:{plain_text}"))
        )
        message_id = str(source_id)
        code_references = self._extract_code(content_node, message_id)
        image_references = self._extract_images(content_node, message_id, base_url)
        attachment_references, citation_references = self._extract_links(content_node, message_id, base_url)
        table_references = self._extract_tables(content_node, message_id)
        timestamp = self._extract_timestamp(node)
        return ConversationMessage(
            message_id=message_id,
            sequence_number=sequence_number,
            role=role,
            plain_text=plain_text,
            markdown=markdown,
            html=html,
            code_references=code_references,
            image_references=image_references,
            attachment_references=attachment_references,
            table_references=table_references,
            citation_references=citation_references,
            timestamp=timestamp,
            character_count=len(plain_text),
            word_count=word_count(plain_text),
            estimated_tokens=estimated_tokens(plain_text),
        )

    @staticmethod
    def _content_node(node: Tag) -> Tag:
        selectors = (
            "[data-message-content]",
            ".markdown",
            "[class*='markdown']",
            "[class*='prose']",
        )
        for selector in selectors:
            found = node.select_one(selector)
            if isinstance(found, Tag):
                return found
        return node

    @staticmethod
    def _extract_role(node: Tag) -> str:
        role = str(node.get("data-message-author-role", "")).lower().strip()
        if role in {"user", "assistant", "system", "tool"}:
            return role
        test_id = str(node.get("data-testid", "")).lower()
        classes = " ".join(node.get("class", [])).lower()
        combined = f"{test_id} {classes}"
        for supported in ("assistant", "user", "system", "tool"):
            if supported in combined:
                return supported
        return "unknown"

    @staticmethod
    def _extract_code(content_node: Tag, message_id: str) -> list[CodeReference]:
        output: list[CodeReference] = []
        for index, code_node in enumerate(content_node.select("pre code"), start=1):
            raw_code = code_node.get_text("", strip=False)
            classes = list(code_node.get("class", [])) + list(code_node.parent.get("class", []))
            language = "text"
            for class_name in classes:
                match = _LANGUAGE_CLASS_PATTERN.search(str(class_name))
                if match:
                    language = match.group(1).lower()
                    break
            output.append(
                CodeReference(
                    id=f"{message_id}-code-{index:03d}",
                    language=language,
                    raw_code=raw_code,
                    character_count=len(raw_code),
                    line_count=len(raw_code.splitlines()),
                )
            )
        return output

    @staticmethod
    def _extract_images(content_node: Tag, message_id: str, base_url: str) -> list[ImageReference]:
        output: list[ImageReference] = []
        seen: set[str] = set()
        for index, image in enumerate(content_node.select("img"), start=1):
            source = str(image.get("src") or image.get("data-src") or "").strip()
            if not source:
                continue
            absolute_source = urljoin(base_url, source)
            if absolute_source in seen:
                continue
            seen.add(absolute_source)
            width = _to_int(image.get("width"))
            height = _to_int(image.get("height"))
            output.append(
                ImageReference(
                    id=f"{message_id}-image-{index:03d}",
                    source_url=absolute_source,
                    alt_text=str(image.get("alt") or ""),
                    width=width,
                    height=height,
                )
            )
        return output

    @staticmethod
    def _extract_links(
        content_node: Tag,
        message_id: str,
        base_url: str,
    ) -> tuple[list[AttachmentReference], list[CitationReference]]:
        attachments: list[AttachmentReference] = []
        citations: list[CitationReference] = []
        seen: set[str] = set()
        for index, anchor in enumerate(content_node.select("a[href]"), start=1):
            source = urljoin(base_url, str(anchor.get("href") or "").strip())
            if not source or source in seen:
                continue
            seen.add(source)
            label = anchor.get_text(" ", strip=True)
            parsed = urlparse(source)
            filename = Path(parsed.path).name
            suffix = Path(filename).suffix.lower()
            attributes = " ".join(
                [
                    str(anchor.get("data-testid") or ""),
                    str(anchor.get("aria-label") or ""),
                    " ".join(str(value) for value in anchor.get("class", [])),
                ]
            ).lower()
            label_suffix = Path(label).suffix.lower()
            is_attachment = (
                anchor.has_attr("download")
                or suffix in SUPPORTED_ASSET_EXTENSIONS
                or label_suffix in SUPPORTED_ASSET_EXTENSIONS
                or any(marker in attributes for marker in ("attachment", "download", "file"))
            )
            if is_attachment:
                attachments.append(
                    AttachmentReference(
                        id=f"{message_id}-attachment-{index:03d}",
                        source_url=source,
                        original_name=filename or label or f"attachment-{index:03d}",
                    )
                )
            elif parsed.scheme in {"http", "https"}:
                citations.append(
                    CitationReference(
                        id=f"{message_id}-citation-{index:03d}",
                        url=source,
                        label=label,
                    )
                )
        return attachments, citations

    @staticmethod
    def _extract_tables(content_node: Tag, message_id: str) -> list[TableReference]:
        output: list[TableReference] = []
        for index, table in enumerate(content_node.select("table"), start=1):
            rows: list[list[str]] = []
            headers: list[str] = []
            for row_index, row in enumerate(table.select("tr")):
                values = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
                if not values:
                    continue
                if row_index == 0 and row.select("th"):
                    headers = values
                else:
                    rows.append(values)
            markdown = _table_markdown(headers, rows)
            output.append(
                TableReference(
                    id=f"{message_id}-table-{index:03d}",
                    headers=headers,
                    rows=rows,
                    html=str(table),
                    markdown=markdown,
                )
            )
        return output

    @staticmethod
    def _extract_timestamp(node: Tag) -> datetime | None:
        candidates = (
            node.get("data-message-timestamp"),
            node.get("data-timestamp"),
        )
        time_node = node.select_one("time[datetime]")
        if time_node is not None:
            candidates = (*candidates, time_node.get("datetime"))
        for value in candidates:
            if not value:
                continue
            text = str(value).strip().replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(text)
            except ValueError:
                continue
        return None

    @staticmethod
    def _conversation_created_at(soup: BeautifulSoup) -> datetime | None:
        metadata = soup.select_one("meta[property='article:published_time'], meta[name='created-at']")
        if metadata is None:
            return None
        value = str(metadata.get("content") or "").replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _conversation_id(url: str, title: str) -> str:
        match = _CONVERSATION_ID_PATTERN.search(url)
        if match:
            return match.group(1)
        return str(uuid5(NAMESPACE_URL, f"{url}|{title}"))

    @staticmethod
    def _resequence_and_link(messages: list[ConversationMessage]) -> None:
        for index, message in enumerate(messages):
            message.sequence_number = index + 1
            message.parent_message_id = messages[index - 1].message_id if index > 0 else None
            message.child_message_id = messages[index + 1].message_id if index + 1 < len(messages) else None

    @staticmethod
    def _detect_language(text: str) -> str:
        if not text.strip():
            return "unknown"
        bengali = sum(1 for character in text if "\u0980" <= character <= "\u09ff")
        latin = sum(1 for character in text if character.isascii() and character.isalpha())
        if bengali > latin * 0.25:
            return "bn"
        if latin:
            return "en"
        return "unknown"


def _to_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _table_markdown(headers: list[str], rows: list[list[str]]) -> str:
    column_count = max([len(headers), *(len(row) for row in rows)], default=0)
    if column_count == 0:
        return ""
    normalized_headers = headers or [f"Column {index}" for index in range(1, column_count + 1)]
    normalized_headers += [""] * (column_count - len(normalized_headers))

    def render(values: list[str]) -> str:
        padded = values + [""] * (column_count - len(values))
        escaped = [value.replace("|", "\\|").replace("\n", " ") for value in padded[:column_count]]
        return "| " + " | ".join(escaped) + " |"

    output = [render(normalized_headers), "| " + " | ".join("---" for _ in range(column_count)) + " |"]
    output.extend(render(row) for row in rows)
    return "\n".join(output)
