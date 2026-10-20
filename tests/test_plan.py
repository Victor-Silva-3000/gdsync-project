import tempfile
import unittest
from pathlib import Path

from gdsync.plan import choose_remote, decide, file_md5, select_sync_target


class PlanTests(unittest.TestCase):
    def test_md5_of_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "note.txt"
            path.write_bytes(b"abc")
            self.assertEqual(file_md5(path), "900150983cd24fb0d6963f7d28e17f72")

    def test_choose_newest(self):
        older = {"id": "a", "modifiedTime": "2020-01-01T00:00:00Z"}
        newer = {"id": "b", "modifiedTime": "2024-01-01T00:00:00Z"}
        self.assertEqual(choose_remote([older, newer])["id"], "b")

    def test_native_google_file_is_not_an_update_target(self):
        doc = {"id": "doc", "mimeType": "application/vnd.google-apps.document", "modifiedTime": "2024-01-01T00:00:00Z"}
        binary = {"id": "bin", "mimeType": "application/pdf", "modifiedTime": "2020-01-01T00:00:00Z"}
        target, binaries, natives = select_sync_target([doc, binary])
        self.assertEqual(target["id"], "bin")
        self.assertEqual([item["id"] for item in binaries], ["bin"])
        self.assertEqual(natives[0]["id"], "doc")

    def test_decide(self):
        remote = {"md5Checksum": "abc"}
        self.assertEqual(decide("abc", remote, force=False, always_new=False), "skip")
        self.assertEqual(decide("abc", remote, force=True, always_new=False), "update")
        self.assertEqual(decide("zzz", remote, force=False, always_new=False), "update")
        self.assertEqual(decide("abc", remote, force=False, always_new=True), "create")
        self.assertEqual(decide(None, None, force=False, always_new=False), "create")
