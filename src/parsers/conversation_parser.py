"""Resilient HTML-to-domain conversation parser."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse
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
_FAVICON_PATH_NAMES = frozenset({"favicon", "favicons", "favicon.ico"})
_FAVICON_QUERY_KEYS = frozenset({"domain", "domain_url", "host", "site", "url"})


class ConversationParser:
    """Convert fully loaded conversation HTML into validated domain models."""

    MESSAGE_SELECTORS = (
        "[data-message-author-role]",
        "[data-message-id]",
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
        exported_at_local: datetime | None = None,
        export_id: str | None = None,
        browser_name: str = "unavailable",
        browser_version: str = "unavailable",
        browser_profile: str = "unavailable",
        chatgpt_workspace: str | None = None,
        chatgpt_model: str | None = None,
        estimated_size: int = 0,
        source_message_count: int | None = None,
        source_asset_counts: dict[str, int] | None = None,
        readiness: dict[str, Any] | None = None,
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

        return self.build_record(
            messages=messages,
            url=url,
            title=title,
            platform_name=platform_name,
            exported_at=exported_at,
            exported_at_local=exported_at_local,
            export_id=export_id,
            browser_name=browser_name,
            browser_version=browser_version,
            browser_profile=browser_profile,
            chatgpt_workspace=chatgpt_workspace,
            chatgpt_model=chatgpt_model,
            estimated_size=estimated_size,
            source_message_count=source_message_count,
            source_asset_counts=source_asset_counts,
            readiness=readiness,
            created_at=self._conversation_created_at(soup),
        )

    def parse_message_fragment(
        self,
        *,
        html: str,
        sequence_number: int,
        conversation_id: str,
        base_url: str,
        captured_at: datetime | None = None,
        source_key: str = "",
        source_signature: str = "",
        capture_attempts: int = 1,
    ) -> ConversationMessage:
        """Parse one observed message fragment into a validated domain message."""
        soup = BeautifulSoup(html, "html.parser")
        node = self._first_message_node(soup)
        if node is None:
            raise ValueError("Message fragment does not contain a supported ChatGPT message container.")
        message = self._parse_message(
            node=node,
            sequence_number=sequence_number,
            conversation_id=conversation_id,
            base_url=base_url,
        )
        message.captured_at = captured_at or datetime.now(UTC)
        message.source_key = source_key or message.message_id
        message.source_signature = source_signature
        message.capture_attempts = max(1, int(capture_attempts))
        message.capture_status = "verified"
        message.capture_error = None
        if message.timestamp is not None:
            message.timestamp_source = "message_timestamp"
        return message

    def build_record(
        self,
        *,
        messages: list[ConversationMessage],
        url: str,
        title: str,
        exported_at: datetime,
        platform_name: str = "ChatGPT",
        exported_at_local: datetime | None = None,
        export_id: str | None = None,
        browser_name: str = "unavailable",
        browser_version: str = "unavailable",
        browser_profile: str = "unavailable",
        chatgpt_workspace: str | None = None,
        chatgpt_model: str | None = None,
        estimated_size: int = 0,
        source_message_count: int | None = None,
        source_asset_counts: dict[str, int] | None = None,
        readiness: dict[str, Any] | None = None,
        capture_warnings: list[str] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> ConversationRecord:
        """Build a complete conversation from ordered verified/degraded messages."""
        ordered = [message.model_copy(deep=True) for message in messages]
        self._resequence_and_link(ordered)

        inferred_created = created_at
        inferred_updated = updated_at
        timestamp_source = "unknown"
        if ordered and inferred_created is None and inferred_updated is None:
            first = ordered[0]
            last = ordered[-1]
            if (
                first.timestamp is not None
                and last.timestamp is not None
                and first.timestamp_source == "message_timestamp"
                and last.timestamp_source == "message_timestamp"
            ):
                inferred_created = first.timestamp
                inferred_updated = last.timestamp
                timestamp_source = "message_timestamp"
        elif inferred_created is not None and inferred_updated is not None:
            timestamp_source = "page_state"

        duration_seconds: int | None = None
        if inferred_created is not None and inferred_updated is not None:
            delta = int((inferred_updated - inferred_created).total_seconds())
            if delta >= 0:
                duration_seconds = delta

        local_export = exported_at_local or exported_at.astimezone()
        timezone = _timezone_name(local_export)
        combined_text = "\n".join(message.plain_text for message in ordered)
        record_data: dict[str, Any] = {
            "conversation_id": self._conversation_id(url, title),
            "title": title.strip() or "Untitled Conversation",
            "url": url,
            "platform_name": platform_name,
            "created_at": inferred_created,
            "updated_at": inferred_updated,
            "exported_at": exported_at,
            "exported_at_local": local_export,
            "timezone": timezone,
            "timestamp_source": timestamp_source,
            "duration_seconds": duration_seconds,
            "language": self._detect_language(combined_text),
            "browser_name": browser_name or "unavailable",
            "browser_version": browser_version or "unavailable",
            "browser_profile": browser_profile or "unavailable",
            "chatgpt_workspace": chatgpt_workspace,
            "chatgpt_model": chatgpt_model,
            "estimated_size": max(0, int(estimated_size)),
            "source_message_count": source_message_count,
            "source_asset_counts": dict(source_asset_counts or {}),
            "readiness": dict(readiness or {}),
            "skipped_message_count": sum(message.capture_status == "skipped" for message in ordered),
            "capture_warnings": list(capture_warnings or []),
            "messages": ordered,
        }
        if export_id:
            record_data["export_id"] = export_id
        return ConversationRecord.model_validate(record_data)

    def _first_message_node(self, soup: BeautifulSoup) -> Tag | None:
        nodes = self._find_message_nodes(soup)
        return nodes[0] if nodes else None

    def _find_message_nodes(self, soup: BeautifulSoup) -> list[Tag]:
        """Return every supported message container in document order.

        ChatGPT can mix conversation-turn wrappers, data-message-id wrappers,
        and role-bearing descendants in the same document. Selecting the first
        non-empty selector family silently drops messages from other families.
        The combined selector plus outermost-container de-duplication preserves
        mixed layouts while avoiding nested duplicate parsing.
        """
        selector = ", ".join(self.MESSAGE_SELECTORS)
        candidates = [node for node in soup.select(selector) if isinstance(node, Tag)]
        return self._remove_nested_candidates(candidates, None)

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
        nested_message = node.select_one("[data-message-id]")
        nested_turn = node.select_one("[data-testid^='conversation-turn']")
        source_id = (
            node.get("data-message-id")
            or (nested_message.get("data-message-id") if isinstance(nested_message, Tag) else None)
            or node.get("data-testid")
            or (nested_turn.get("data-testid") if isinstance(nested_turn, Tag) else None)
            or node.get("id")
            or str(uuid5(NAMESPACE_URL, f"{conversation_id}:{sequence_number}:{role}:{plain_text}"))
        )
        message_id = str(source_id)
        code_references = self._extract_code(content_node, message_id)
        image_references = self._extract_images(content_node, message_id, base_url)
        attachment_references, citation_references = self._extract_links(node, message_id, base_url)
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
        nested_role = node.select_one("[data-message-author-role]")
        if isinstance(nested_role, Tag):
            role = str(nested_role.get("data-message-author-role", "")).lower().strip()
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
            if _is_decorative_favicon_source(absolute_source):
                LOGGER.debug("Decorative favicon excluded from image assets: %s", absolute_source)
                continue
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
        candidates = content_node.select(
            "a[href], [data-download-url], [data-file-url], [data-href], [data-url], "
            "[data-file-id], [data-filename], [data-file-name], "
            "[data-testid*=file], [data-testid*=download], "
            "[aria-label*=Download], [aria-label*=download]"
        )
        for index, node in enumerate(candidates, start=1):
            label = node.get_text(" ", strip=True)
            attributes = " ".join(
                [
                    str(node.get("download") or ""),
                    str(node.get("data-testid") or ""),
                    str(node.get("aria-label") or ""),
                    str(node.get("data-file-id") or ""),
                    str(node.get("data-filename") or ""),
                    str(node.get("data-file-name") or ""),
                    " ".join(str(value) for value in node.get("class", [])),
                ]
            ).lower()
            source_value = next(
                (
                    str(node.get(attribute) or "").strip()
                    for attribute in ("href", "data-download-url", "data-file-url", "data-href", "data-url")
                    if str(node.get(attribute) or "").strip()
                ),
                "",
            )
            absolute_source = urljoin(base_url, source_value) if source_value else ""
            filename = _attachment_filename(node, absolute_source, label)
            parsed = urlparse(absolute_source)
            suffix = Path(filename).suffix.lower()
            label_suffix = Path(label).suffix.lower()
            path_and_query = f"{parsed.path}?{parsed.query}".lower()
            has_file_identity = bool(
                str(node.get("data-file-id") or "").strip()
                or str(node.get("data-filename") or "").strip()
                or str(node.get("data-file-name") or "").strip()
            )
            semantic_attachment = bool(
                re.search(r"(?:^|[\s_-])(attachment|download|file)(?:$|[\s_-])", attributes)
            )
            is_attachment = (
                node.has_attr("download")
                or suffix in SUPPORTED_ASSET_EXTENSIONS
                or label_suffix in SUPPORTED_ASSET_EXTENSIONS
                or semantic_attachment
                or any(
                    marker in path_and_query
                    for marker in ("/backend-api/files/", "/files/", "file-service", "download=")
                )
                or parsed.scheme in {"sandbox", "blob"}
                or has_file_identity
            )
            if is_attachment:
                source = absolute_source or _synthetic_attachment_source(node, message_id, filename, index)
                if not source or source in seen:
                    continue
                seen.add(source)
                attachments.append(
                    AttachmentReference(
                        id=f"{message_id}-attachment-{index:03d}",
                        source_url=source,
                        original_name=filename or f"attachment-{index:03d}",
                    )
                )
            elif parsed.scheme in {"http", "https"}:
                if absolute_source in seen:
                    continue
                seen.add(absolute_source)
                citations.append(
                    CitationReference(
                        id=f"{message_id}-citation-{index:03d}",
                        url=absolute_source,
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
            parsed = _parse_datetime_value(value)
            if parsed is not None:
                return parsed
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


def _parse_datetime_value(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        numeric = float(text)
    except ValueError:
        numeric = None
    if numeric is not None:
        if numeric > 10_000_000_000:
            numeric /= 1000.0
        try:
            return datetime.fromtimestamp(numeric, UTC)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _timezone_name(value: datetime) -> str:
    name = value.tzname()
    if name:
        return name
    offset = value.utcoffset()
    if offset is None:
        return "unknown"
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _synthetic_attachment_source(node: Tag, message_id: str, filename: str, index: int) -> str:
    """Build a stable locator only when ChatGPT exposes no direct file URL."""
    file_id = str(node.get("data-file-id") or "").strip()
    query_parts = [f"messageId={quote(message_id, safe='')}", f"index={index}"]
    if file_id:
        query_parts.append(f"fileId={quote(file_id, safe='')}")
    if filename:
        query_parts.append(f"filename={quote(filename, safe='')}")
    if not file_id and not filename:
        return ""
    return "contextvault-chatgpt-attachment:?" + "&".join(query_parts)


def _is_decorative_favicon_source(source_url: str) -> bool:
    """Return whether a message image URL is a citation/UI favicon, not content."""
    parsed = urlparse(source_url)
    path_name = Path(unquote(parsed.path).rstrip("/")).name.casefold()
    if path_name == "favicons":
        return True
    if path_name not in _FAVICON_PATH_NAMES:
        return False
    query_keys = {key.casefold() for key in parse_qs(parsed.query)}
    return bool(query_keys & _FAVICON_QUERY_KEYS)


def _attachment_filename(node: Tag, source: str, label: str) -> str:
    """Resolve the best available attachment filename without inventing metadata."""
    parsed = urlparse(source)
    query = parse_qs(parsed.query)
    candidates: list[str] = [
        str(node.get("download") or ""),
        str(node.get("data-filename") or ""),
        str(node.get("data-file-name") or ""),
        *(query.get("filename") or []),
        *(query.get("file_name") or []),
        Path(parsed.path).name,
        label,
    ]
    for candidate in candidates:
        clean = unquote(str(candidate or "")).strip().strip('"')
        if not clean:
            continue
        clean = re.sub(r"^(?:download|file|attachment)\s*[:\-]\s*", "", clean, flags=re.IGNORECASE)
        if clean:
            return clean
    return ""


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
