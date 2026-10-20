import unittest

from gdsync.cli import split_sources_dest
from gdsync.resolve import FolderSpecError


class SplitTests(unittest.TestCase):
    def test_last_positional_is_destination(self):
        sources, dest = split_sources_dest(["a.pdf", "b.pdf", "invoices"], None)
        self.assertEqual(sources, ["a.pdf", "b.pdf"])
        self.assertEqual(dest, "invoices")

    def test_to_flag_keeps_every_source(self):
        sources, dest = split_sources_dest(["a.pdf", "b.pdf"], "invoices")
        self.assertEqual(sources, ["a.pdf", "b.pdf"])
        self.assertEqual(dest, "invoices")

    def test_missing_destination(self):
        with self.assertRaises(FolderSpecError):
            split_sources_dest(["a.pdf"], None)
