import unittest

from gdsync.resolve import (
    AmbiguousFolder,
    FolderNotFound,
    FolderSpecError,
    canonical_alias_value,
    classify_folder,
    escape_query,
    file_query,
    resolve_target,
)


class ResolveTests(unittest.TestCase):
    def test_folder_url_shapes(self):
        urls = [
            "https://drive.google.com/drive/folders/1AbCdefGhijkLmnoPqrstuvwx",
            "https://drive.google.com/drive/u/1/folders/1AbCdefGhijkLmnoPqrstuvwx?usp=sharing",
            "https://drive.google.com/open?id=1AbCdefGhijkLmnoPqrstuvwx",
        ]
        for url in urls:
            target = classify_folder(url)
            self.assertEqual(target.kind, "id")
            self.assertEqual(target.value, "1AbCdefGhijkLmnoPqrstuvwx")

    def test_file_url_rejected(self):
        with self.assertRaises(FolderSpecError):
            classify_folder("https://drive.google.com/file/d/1AbCdefGhijkLmnoPqrstuvwx/view")

    def test_alias_then_id(self):
        target = classify_folder("invoices", {"invoices": "id:1AbCdefGhijkLmnoPqrstuvwx"})
        self.assertEqual(target, classify_folder("1AbCdefGhijkLmnoPqrstuvwx"))

    def test_path_and_prefixes(self):
        self.assertEqual(classify_folder(r"Work\2026").value, "Work/2026")
        self.assertEqual(classify_folder("path:1AbCdefGhijkLmnoPqrstuvwx").kind, "path")
        self.assertEqual(classify_folder("Reports").kind, "path")
        self.assertEqual(classify_folder("/").value, "root")

    def test_parent_dotdot_rejected(self):
        with self.assertRaises(FolderSpecError):
            classify_folder("Work/../Secret")

    def test_escape_and_query(self):
        self.assertEqual(escape_query("o'brien"), r"o\'brien")
        query = file_query("root", "a'b")
        self.assertIn(r"name = 'a\'b'", query)
        self.assertIn("mimeType !=", query)

    def test_walk_path(self):
        tree = {
            ("root", "Work"): [{"id": "w"}],
            ("w", "2026"): [{"id": "y"}],
        }

        def find(parent, name):
            return tree.get((parent, name), [])

        target = classify_folder("Work/2026")
        self.assertEqual(resolve_target(target, find), "y")

    def test_missing_and_ambiguous(self):
        def find(parent, name):
            if name == "Dup":
                return [{"id": "1"}, {"id": "2"}]
            return []

        with self.assertRaises(FolderNotFound):
            resolve_target(classify_folder("Missing"), find)
        with self.assertRaises(AmbiguousFolder):
            resolve_target(classify_folder("Dup"), find)

    def test_mkdir_callback(self):
        created = []

        def find(_parent, _name):
            return []

        def mkdir(parent, name):
            created.append((parent, name))
            return "new-id"

        self.assertEqual(resolve_target(classify_folder("New"), find, mkdir), "new-id")
        self.assertEqual(created, [("root", "New")])

    def test_canonical_alias(self):
        self.assertEqual(canonical_alias_value("Reports/2026"), "path:Reports/2026")
        self.assertTrue(canonical_alias_value("https://drive.google.com/drive/folders/1AbCdefGhijkLmnoPqrstuvwx").startswith("id:"))
