from __future__ import annotations

import io
import tempfile
import threading
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.core.archive_builder import ArchiveBuilder
from src.core.archive_validator import ArchiveValidator
from src.models.settings import ApplicationSettings
from src.parsers.conversation_parser import ConversationParser
from src.services.archive_repository import ArchiveRepository
from src.utils.json_io import read_json


class ArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        html = Path("tests/fixtures/sample_conversation.html").read_text(encoding="utf-8")
        self.conversation = ConversationParser().parse(
            html=html,
            url="https://chatgpt.com/c/sample-id",
            title="Sample Conversation",
            exported_at=datetime(2026, 7, 28, tzinfo=UTC),
        )
        image = Image.new("RGB", (20, 10), (255, 255, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        self.png = buffer.getvalue()

    def resource_loader(self, url: str) -> dict[str, object]:
        if url.endswith(".png"):
            return {"content": self.png, "contentType": "image/png", "suggestedFilename": "diagram.png"}
        if url.endswith(".pdf"):
            return {"content": b"%PDF-1.4\n% ContextVault test\n", "contentType": "application/pdf", "suggestedFilename": "spec.pdf"}
        raise AssertionError(f"Unexpected resource: {url}")

    def test_verified_byte_write_uses_short_same_directory_temporary_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / ("a" * 75) / ("b" * 75)
            target = parent / "0002-b8f44655-aaf7-4087-b7af-114f5f37dc32-code-001.txt"
            payload = b"line-one\r\nline-two\r\n"
            legacy_temporary = target.parent / f".{target.name}.partial-{'0' * 32}"
            self.assertLess(len(str(target)), 260)
            self.assertGreaterEqual(len(str(legacy_temporary)), 260)

            created_paths: list[Path] = []
            real_named_temporary_file = tempfile.NamedTemporaryFile

            def tracked_named_temporary_file(*args: object, **kwargs: object):
                stream = real_named_temporary_file(*args, **kwargs)
                created_paths.append(Path(stream.name))
                return stream

            with patch(
                "src.core.archive_builder.tempfile.NamedTemporaryFile",
                side_effect=tracked_named_temporary_file,
            ):
                ArchiveBuilder._write_verified_bytes(
                    target,
                    payload,
                    attempts=1,
                    description="long-path regression code reference",
                )

            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(len(created_paths), 1)
            self.assertEqual(created_paths[0].parent, target.parent)
            self.assertLess(len(str(created_paths[0])), 260)
            self.assertNotIn(target.name, created_paths[0].name)
            self.assertFalse(created_paths[0].exists())

    def test_build_validate_and_rebuild_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = ApplicationSettings.model_validate(
                {
                    "export": {
                        "defaultFolder": directory,
                        "archiveName": "{title}-{id}",
                        "autoCreateFolder": True,
                        "overwrite": False,
                        "compress": True,
                        "verifyExport": True,
                    }
                }
            )
            result = ArchiveBuilder().build(
                conversation=self.conversation,
                settings=settings,
                destination_root=Path(directory),
                resource_loader=self.resource_loader,
                cancellation_event=threading.Event(),
            )
            archive_path = Path(result["archivePath"])
            self.assertTrue(archive_path.is_dir())
            self.assertTrue(Path(result["zipPath"]).is_file())
            self.assertTrue(ArchiveValidator().validate(archive_path).is_valid)
            manifest = read_json(archive_path / "manifest.json")
            self.assertEqual(manifest["data"]["validationStatus"]["status"], "valid")
            self.assertTrue((archive_path / "assets/images/0002-assistant-1-image-001.png").is_file())
            self.assertTrue((archive_path / "assets/attachments/spec.pdf").is_file())
            self.assertTrue((archive_path / "rag/chunks.json").is_file())

            rebuilt = ArchiveRepository().rebuild_summary(archive_path)
            self.assertTrue(rebuilt["validation"]["isValid"])
            self.assertTrue(ArchiveValidator().validate(archive_path).is_valid)


    def test_failed_overwrite_preserves_previous_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            existing = destination / "Sample Conversation-sample-id"
            existing.mkdir()
            marker = existing / "previous-release.txt"
            marker.write_text("preserve me", encoding="utf-8")
            settings = ApplicationSettings.model_validate(
                {
                    "export": {
                        "defaultFolder": directory,
                        "archiveName": "{title}-{id}",
                        "autoCreateFolder": True,
                        "overwrite": True,
                        "compress": False,
                        "verifyExport": True,
                    }
                }
            )

            def failing_loader(_url: str) -> dict[str, object]:
                raise OSError("simulated authenticated download failure")

            with self.assertRaises(OSError):
                ArchiveBuilder().build(
                    conversation=self.conversation,
                    settings=settings,
                    destination_root=destination,
                    resource_loader=failing_loader,
                    cancellation_event=threading.Event(),
                )
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve me")
            self.assertFalse(any(".partial-" in path.name for path in destination.iterdir()))

    def test_overwrite_replaces_folder_and_zip_without_numbered_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            settings = ApplicationSettings.model_validate(
                {
                    "export": {
                        "defaultFolder": directory,
                        "archiveName": "{title}-{id}",
                        "autoCreateFolder": True,
                        "overwrite": True,
                        "compress": True,
                        "verifyExport": True,
                    }
                }
            )
            builder = ArchiveBuilder()
            first = builder.build(
                conversation=self.conversation,
                settings=settings,
                destination_root=destination,
                resource_loader=self.resource_loader,
                cancellation_event=threading.Event(),
            )
            second = builder.build(
                conversation=self.conversation,
                settings=settings,
                destination_root=destination,
                resource_loader=self.resource_loader,
                cancellation_event=threading.Event(),
            )
            self.assertEqual(first["archivePath"], second["archivePath"])
            self.assertEqual(first["zipPath"], second["zipPath"])
            self.assertEqual(len(list(destination.glob("*.zip"))), 1)
            self.assertFalse(any(".backup-" in path.name or ".partial-" in path.name for path in destination.iterdir()))


    def test_validator_rejects_missing_manifest_hash_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = ApplicationSettings.model_validate(
                {
                    "export": {
                        "defaultFolder": directory,
                        "archiveName": "{title}-{id}",
                        "autoCreateFolder": True,
                        "overwrite": False,
                        "compress": False,
                        "verifyExport": True,
                    }
                }
            )
            result = ArchiveBuilder().build(
                conversation=self.conversation,
                settings=settings,
                destination_root=Path(directory),
                resource_loader=self.resource_loader,
                cancellation_event=threading.Event(),
            )
            archive_path = Path(result["archivePath"])
            manifest_path = archive_path / "manifest.json"
            manifest = read_json(manifest_path)
            manifest["data"]["hashInformation"] = [
                entry for entry in manifest["data"]["hashInformation"] if entry["path"] != "metadata.json"
            ]
            from src.utils.json_io import write_json

            write_json(manifest_path, manifest)
            validation = ArchiveValidator().validate(archive_path)
            self.assertFalse(validation.is_valid)
            self.assertTrue(any("missing hash entries" in error for error in validation.errors))

    def test_cancellation_removes_staging_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cancelled = threading.Event()
            cancelled.set()
            with self.assertRaises(InterruptedError):
                ArchiveBuilder().build(
                    conversation=self.conversation,
                    settings=ApplicationSettings(),
                    destination_root=Path(directory),
                    resource_loader=self.resource_loader,
                    cancellation_event=cancelled,
                )
            self.assertEqual(list(Path(directory).iterdir()), [])


class ArchiveValidatorRegressionTests(unittest.TestCase):
    def _build_archive(self, directory: str) -> Path:
        html = Path("tests/fixtures/sample_conversation.html").read_text(encoding="utf-8")
        conversation = ConversationParser().parse(
            html=html,
            url="https://chatgpt.com/c/validator-regression",
            title="Validator Regression",
            exported_at=datetime(2026, 7, 28, tzinfo=UTC),
        )
        image = Image.new("RGB", (4, 4), (255, 255, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        png = buffer.getvalue()

        def loader(url: str) -> dict[str, object]:
            if url.endswith(".png"):
                return {"content": png, "contentType": "image/png", "suggestedFilename": "diagram.png"}
            return {"content": b"%PDF-1.4\n", "contentType": "application/pdf", "suggestedFilename": "spec.pdf"}

        settings = ApplicationSettings.model_validate(
            {"export": {"archiveName": "validator", "overwrite": True, "verifyExport": True}}
        )
        result = ArchiveBuilder().build(
            conversation=conversation,
            settings=settings,
            destination_root=Path(directory),
            resource_loader=loader,
            cancellation_event=threading.Event(),
        )
        return Path(result["archivePath"])

    def test_validator_recomputes_message_counts_and_links(self) -> None:
        from src.utils.json_io import write_json

        with tempfile.TemporaryDirectory() as directory:
            archive = self._build_archive(directory)
            conversation_path = archive / "conversation.json"
            payload = read_json(conversation_path)
            payload["data"]["messages"][0]["characterCount"] += 1
            payload["data"]["messages"][0]["childMessageId"] = None
            write_json(conversation_path, payload)
            validation = ArchiveValidator().validate(archive, verify_hashes=False)
            self.assertFalse(validation.is_valid)
            self.assertTrue(any("characterCount" in error for error in validation.errors))
            self.assertTrue(any("childMessageId" in error for error in validation.errors))

    def test_validator_recomputes_asset_hashes_and_rag_counts(self) -> None:
        from src.utils.json_io import write_json

        with tempfile.TemporaryDirectory() as directory:
            archive = self._build_archive(directory)
            conversation_path = archive / "conversation.json"
            payload = read_json(conversation_path)
            image_reference = payload["data"]["messages"][1]["imageReferences"][0]
            image_reference["sha256"] = "0" * 64
            write_json(conversation_path, payload)

            chunks_path = archive / "rag/chunks.json"
            chunks = read_json(chunks_path)
            chunks["data"]["chunks"][0]["wordCount"] += 1
            write_json(chunks_path, chunks)

            validation = ArchiveValidator().validate(archive, verify_hashes=False)
            self.assertFalse(validation.is_valid)
            self.assertTrue(any("sha256" in error for error in validation.errors))
            self.assertTrue(any("RAG chunk" in error and "wordCount" in error for error in validation.errors))

if __name__ == "__main__":
    unittest.main()
