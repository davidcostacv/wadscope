import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wadscope.archive import FormatError, ResourceLimitError, WadArchive
from tests.fixtures import directory_entry, header, original_wad


class ExtractTests(unittest.TestCase):
    def setUp(self):
        try:
            self.extract = importlib.import_module("wadscope.extract").extract_lump
        except ModuleNotFoundError:
            self.fail("extraction API has not been implemented")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "original.wad"
        self.source.write_bytes(original_wad())
        self.archive = WadArchive.open(self.source)
        self.addCleanup(self.archive.close)
        self.output = self.root / "chosen.bin"

    def test_indexes_disambiguate_duplicates_and_zero_marker(self):
        for index, data in enumerate((b"ABCD", b"CDEF", b"")):
            output = self.root / str(index)
            self.assertEqual(self.extract(self.archive, index, output), output)
            self.assertEqual(output.read_bytes(), data)

    def test_names_never_determine_output_path(self):
        self.archive.close()
        self.source.write_bytes(header(1, 16) + b"DATA" + directory_entry(12, 4, b"../evil!"))
        with WadArchive.open(self.source) as archive:
            self.extract(archive, 0, self.output)
        self.assertEqual(self.output.read_bytes(), b"DATA")
        self.assertEqual({p.name for p in self.root.iterdir()}, {"original.wad", "chosen.bin"})

    def test_no_overwrite_preserves_existing_file(self):
        self.output.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            self.extract(self.archive, 0, self.output)
        self.assertEqual(self.output.read_bytes(), b"existing")
        self.assertEqual(len(list(self.root.iterdir())), 2)

    def test_successful_overwrite(self):
        self.output.write_bytes(b"existing")
        self.extract(self.archive, 1, self.output, overwrite=True)
        self.assertEqual(self.output.read_bytes(), b"CDEF")

    def test_truncation_preserves_overwrite_and_removes_partial_new_file(self):
        self.archive.close()
        payload = b"A" * 70000
        self.source.write_bytes(header(1, 70012) + payload + directory_entry(12, 70000))
        with WadArchive.open(self.source) as archive:
            with self.source.open("r+b") as stream:
                stream.truncate(65548)
            self.output.write_bytes(b"existing")
            with self.assertRaises(FormatError):
                self.extract(archive, 0, self.output, overwrite=True)
            self.assertEqual(self.output.read_bytes(), b"existing")
            new_output = self.root / "new.bin"
            with self.assertRaises(FormatError):
                self.extract(archive, 0, new_output)
            self.assertFalse(new_output.exists())
        self.assertEqual({p.name for p in self.root.iterdir()}, {"original.wad", "chosen.bin"})

    def test_missing_parent_is_not_created(self):
        with self.assertRaises(FileNotFoundError):
            self.extract(self.archive, 0, self.root / "missing" / "out")
        self.assertFalse((self.root / "missing").exists())

    def test_source_destination_and_hardlink_alias_are_refused(self):
        with self.assertRaises(ValueError):
            self.extract(self.archive, 0, self.source, overwrite=True)
        os.link(self.source, self.output)
        with self.assertRaises(ValueError):
            self.extract(self.archive, 0, self.output, overwrite=True)
        self.assertEqual(self.source.read_bytes(), original_wad())

    def test_invalid_index_and_budget_leave_no_output(self):
        for index in (-1, 3):
            with self.assertRaises(IndexError):
                self.extract(self.archive, index, self.output)
        with WadArchive.open(self.source, max_lump_size=3) as archive:
            with self.assertRaises(ResourceLimitError):
                self.extract(archive, 0, self.output)
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_unsupported_hardlinks_fail_without_output_or_temporary_file(self):
        with patch("os.link", side_effect=OSError("hard links unavailable")):
            with self.assertRaises(OSError):
                self.extract(self.archive, 0, self.output)
        self.assertEqual(list(self.root.iterdir()), [self.source])
