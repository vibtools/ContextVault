from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from src.models.settings import ApplicationSettings
from src.services.config_service import ConfigService
from src.services.history_service import HistoryService
from src.utils.json_io import read_json, write_json


class ServiceTests(unittest.TestCase):
    def test_config_round_trip_and_invalid_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            service = ConfigService(path)
            settings = service.load()
            settings.performance.worker_threads = 2
            service.save(settings)
            self.assertEqual(service.load().performance.worker_threads, 2)
            path.write_text("[]", encoding="utf-8")
            recovered = service.load()
            self.assertEqual(recovered, ApplicationSettings())
            self.assertTrue(path.with_suffix(".json.invalid").is_file())


    def test_json_writer_supports_concurrent_atomic_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "concurrent.json"
            failures: list[BaseException] = []

            def writer(index: int) -> None:
                try:
                    for sequence in range(25):
                        write_json(path, {"writer": index, "sequence": sequence})
                except BaseException as exc:  # test worker must preserve any failure
                    failures.append(exc)

            threads = [threading.Thread(target=writer, args=(index,)) for index in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(failures, [])
            payload = read_json(path)
            self.assertIn(payload["writer"], range(4))
            self.assertIn(payload["sequence"], range(25))
            self.assertEqual([item for item in Path(directory).iterdir() if item.suffix == ".tmp"], [])

    def test_history_is_newest_first_and_bounded_format(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            service = HistoryService(path)
            service.append({"title": "First"})
            service.append({"title": "Second"})
            records = service.list_records()
            self.assertEqual([item["title"] for item in records], ["Second", "First"])
            payload = read_json(path)
            self.assertEqual(payload["schemaVersion"], "1.0")

    def test_json_writer_is_utf8_root_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "value.json"
            write_json(path, {"message": "বাংলা"})
            self.assertEqual(read_json(path)["message"], "বাংলা")
            self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
