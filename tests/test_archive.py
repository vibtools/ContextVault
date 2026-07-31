from __future__ import annotations

import concurrent.futures
import io
import tempfile
import threading
import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from pathlib import Path

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
            exported_at_local=datetime(2026, 7, 28, tzinfo=UTC),
            browser_name="Google Chrome",
            browser_version="138.0",
            browser_profile="Default",
            estimated_size=len(html.encode("utf-8")),
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
                    },
                    "assets": {"attachments": True},
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

    def test_non_overwrite_collision_uses_stable_conversation_identity_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            settings = ApplicationSettings.model_validate(
                {
                    "export": {
                        "defaultFolder": directory,
                        "archiveName": "{title}",
                        "autoCreateFolder": True,
                        "overwrite": False,
                        "compress": False,
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

            self.assertEqual(Path(first["archivePath"]).name, "Sample Conversation")
            self.assertEqual(
                Path(second["archivePath"]).name,
                "Sample Conversation #sampleid",
            )
            self.assertTrue(ArchiveValidator().validate(Path(first["archivePath"])).is_valid)
            self.assertTrue(ArchiveValidator().validate(Path(second["archivePath"])).is_valid)

    def test_concurrent_publish_collision_never_discards_valid_staging(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            staging_roots: list[Path] = []
            for index in range(2):
                staging = Path(tempfile.mkdtemp(prefix=".cv-stage-", dir=destination))
                (staging / "marker.txt").write_text(str(index), encoding="utf-8")
                staging_roots.append(staging)

            barrier = threading.Barrier(2)

            def publish(staging: Path) -> Path:
                barrier.wait(timeout=3)
                return ArchiveBuilder._publish_staging(
                    staging,
                    destination / "Shared Title",
                    destination,
                    overwrite=False,
                    collision_identity="6a5e3c13-f558-83e9-8419-69886adcb4b0",
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                published = list(executor.map(publish, staging_roots))

            self.assertEqual(
                {path.name for path in published},
                {"Shared Title", "Shared Title #6a5e3c13"},
            )
            self.assertEqual(
                sorted((path / "marker.txt").read_text(encoding="utf-8") for path in published),
                ["0", "1"],
            )

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

    def test_verified_byte_writer_uses_short_same_directory_temporary_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            index = 0
            desired_parent_length = 225
            while len(str(parent)) < desired_parent_length:
                remaining = desired_parent_length - len(str(parent)) - 1
                if remaining <= 0:
                    break
                component_length = min(40, remaining)
                prefix = f"s{index:02d}-"
                component = (prefix + ("x" * component_length))[:component_length]
                parent /= component
                index += 1
            parent.mkdir(parents=True)
            target = parent / "code-block.txt"
            legacy_temporary = parent / f".{target.name}.partial-{'a' * 32}"
            self.assertLess(len(str(target)), 260)
            self.assertGreaterEqual(len(str(legacy_temporary)), 260)

            created: list[Path] = []
            original = tempfile.NamedTemporaryFile

            def guarded_temporary(*args: object, **kwargs: object):
                stream = original(*args, **kwargs)
                path = Path(stream.name)
                created.append(path)
                if len(str(path)) >= 260:
                    stream.close()
                    path.unlink(missing_ok=True)
                    raise FileNotFoundError(f"Simulated Windows MAX_PATH rejection: {path}")
                return stream

            payload = b"line1\r\nline2\r\n"
            with patch(
                "src.core.archive_builder.tempfile.NamedTemporaryFile",
                side_effect=guarded_temporary,
            ):
                ArchiveBuilder._write_verified_bytes(
                    target,
                    payload,
                    attempts=1,
                    description="long-path code block",
                )

            self.assertEqual(target.read_bytes(), payload)
            self.assertTrue(created)
            self.assertTrue(all(len(str(path)) < 260 for path in created))
            self.assertFalse(any(path.exists() for path in created))

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
            exported_at_local=datetime(2026, 7, 28, tzinfo=UTC),
            browser_name="Google Chrome",
            browser_version="138.0",
            browser_profile="Default",
            estimated_size=len(html.encode("utf-8")),
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
