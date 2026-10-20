import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gdsync.drive import DriveError, list_folder, sync_file
from gdsync.plan import file_md5
from gdsync.resolve import FOLDER_MIME


class _Done:
    def __init__(self, payload):
        self.payload = payload

    def execute(self, num_retries=0):
        return self.payload


class FakeFiles:
    def __init__(self, meta, children):
        self.meta = meta
        self.children = children
        self.lists = []
        self.created = []
        self.updated = []

    def get(self, **kwargs):
        file_id = kwargs["fileId"]
        if file_id not in self.meta:
            error = Exception("missing")
            error.resp = type("Resp", (), {"status": 404})()
            error.reason = "File not found"
            raise error
        return _Done(self.meta[file_id])

    def list(self, **kwargs):
        self.lists.append(kwargs)
        return _Done({"files": list(self.children)})

    def create(self, **kwargs):
        self.created.append(kwargs)
        body = kwargs["body"]
        return _Done({"id": "created", "name": body["name"], "webViewLink": "https://drive.example/created"})

    def update(self, **kwargs):
        self.updated.append(kwargs)
        return _Done({"id": kwargs["fileId"], "name": "note.txt", "webViewLink": "https://drive.example/updated"})


class FakeService:
    def __init__(self, meta, children):
        self._files = FakeFiles(meta, children)

    def files(self):
        return self._files


def _note(tmp: str) -> Path:
    path = Path(tmp) / "note.txt"
    path.write_text("hello", encoding="utf-8")
    return path


class SyncFlowTests(unittest.TestCase):
    def test_skip_when_checksum_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = _note(tmp)
            service = FakeService(
                {"folder": {"id": "folder", "name": "Invoices", "mimeType": FOLDER_MIME}},
                [
                    {
                        "id": "file1",
                        "name": "note.txt",
                        "mimeType": "text/plain",
                        "md5Checksum": file_md5(local),
                        "modifiedTime": "2024-01-01T00:00:00Z",
                        "webViewLink": "https://drive.example/file1",
                    }
                ],
            )
            result = sync_file(service, local, "id:folder", {})
            self.assertEqual(result.action, "skip")
            self.assertEqual(result.file_id, "file1")
            self.assertEqual(service.files().created, [])
            self.assertEqual(service.files().updated, [])

    def test_shared_drive_list_uses_drive_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = _note(tmp)
            service = FakeService(
                {
                    "folder": {
                        "id": "folder",
                        "name": "Shared",
                        "mimeType": FOLDER_MIME,
                        "driveId": "drive-1",
                    }
                },
                [],
            )
            result = sync_file(service, local, "id:folder", {}, dry_run=True)
            self.assertEqual(result.action, "would-create")
            listed = service.files().lists[0]
            self.assertEqual(listed["corpora"], "drive")
            self.assertEqual(listed["driveId"], "drive-1")
            self.assertTrue(listed["includeItemsFromAllDrives"])

    def test_shortcut_uploads_into_target_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = _note(tmp)
            service = FakeService(
                {
                    "short": {
                        "id": "short",
                        "name": "link",
                        "mimeType": "application/vnd.google-apps.shortcut",
                        "shortcutDetails": {"targetId": "folder"},
                    },
                    "folder": {"id": "folder", "name": "Invoices", "mimeType": FOLDER_MIME},
                },
                [],
            )
            with patch("gdsync.drive._upload", return_value={"id": "created", "name": "note.txt", "webViewLink": "L"}) as upload:
                result = sync_file(service, local, "id:short", {})
            self.assertEqual(result.action, "create")
            self.assertEqual(upload.call_args.args[3], "folder")
            self.assertIsNone(upload.call_args.args[4])

    def test_update_existing_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = _note(tmp)
            service = FakeService(
                {"folder": {"id": "folder", "name": "Invoices", "mimeType": FOLDER_MIME}},
                [
                    {
                        "id": "file1",
                        "name": "note.txt",
                        "mimeType": "text/plain",
                        "md5Checksum": "0" * 32,
                        "modifiedTime": "2024-01-01T00:00:00Z",
                    }
                ],
            )
            with patch("gdsync.drive._upload", return_value={"id": "file1", "name": "note.txt", "webViewLink": "L"}) as upload:
                result = sync_file(service, local, "id:folder", {})
            self.assertEqual(result.action, "update")
            self.assertEqual(upload.call_args.args[4], "file1")

    def test_rejects_non_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = _note(tmp)
            service = FakeService(
                {"folder": {"id": "folder", "name": "notes.txt", "mimeType": "text/plain"}},
                [],
            )
            with self.assertRaises(DriveError):
                sync_file(service, local, "id:folder", {})

    def test_ls_sorts_directories_first(self):
        service = FakeService(
            {"folder": {"id": "folder", "name": "Invoices", "mimeType": FOLDER_MIME}},
            [
                {"id": "b", "name": "b.txt", "mimeType": "text/plain"},
                {"id": "a", "name": "Archive", "mimeType": FOLDER_MIME},
            ],
        )
        folder_id, rows = list_folder(service, "id:folder", {})
        self.assertEqual(folder_id, "folder")
        self.assertEqual([row["name"] for row in rows], ["Archive", "b.txt"])
