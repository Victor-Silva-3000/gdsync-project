import tempfile
import unittest
from pathlib import Path

from gdsync.config import Config
from gdsync.resolve import FolderSpecError


class ConfigTests(unittest.TestCase):
    def test_alias_roundtrip_normalizes_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Config(Path(tmp))
            stored = config.set_alias(
                "invoices",
                "https://drive.google.com/drive/u/0/folders/1AbCdefGhijkLmnoPqrstuvwx?usp=sharing",
            )
            self.assertEqual(stored, "id:1AbCdefGhijkLmnoPqrstuvwx")
            self.assertEqual(config.aliases()["invoices"], stored)

    def test_alias_name_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Config(Path(tmp))
            with self.assertRaises(FolderSpecError):
                config.set_alias("my folder", "root")

    def test_remove_missing_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Config(Path(tmp))
            with self.assertRaises(FolderSpecError):
                config.remove_alias("missing")
