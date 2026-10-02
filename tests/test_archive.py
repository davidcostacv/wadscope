import dataclasses
import importlib
import tempfile
import unittest
from pathlib import Path

from tests.fixtures import directory_entry, header, original_wad


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        try:
            self.api = importlib.import_module("wadscope.archive")
        except ModuleNotFoundError:
            self.fail("archive parser API has not been implemented")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "original.wad"

    def open_bytes(self, data, **options):
        self.path.write_bytes(data)
        archive = self.api.WadArchive.open(self.path, **options)
        self.addCleanup(archive.close)
        return archive

    def chunks(self, archive, index, **options):
        self.assertTrue(hasattr(archive, "iter_lump_chunks"), "chunked extraction API is missing")
        return archive.iter_lump_chunks(index, **options)

    def test_original_fixture_preserves_metadata_and_overlaps(self):
        archive = self.open_bytes(original_wad())
        self.assertEqual((archive.signature, archive.file_size, archive.directory_offset),
                         ("PWAD", 70, 18))
        self.assertIsInstance(archive.entries, tuple)
        self.assertEqual([(e.index, e.offset, e.size, e.name) for e in archive.entries],
                         [(0, 12, 4, "REPEAT"), (1, 14, 4, "REPEAT"), (2, 999, 0, r"M\xff")])
        self.assertEqual(archive.entries[2].raw_name, b"M\xff\0TAIL!")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            archive.entries[0].size = 8
        self.assertEqual(archive.read_lump(0), b"ABCD")
        self.assertEqual(archive.read_lump(1), b"CDEF")
        self.assertEqual(archive.read_lump(2), b"")

    def test_eight_byte_name_and_iwad(self):
        archive = self.open_bytes(header(1, 12, b"IWAD") + directory_entry(0, 0, b"ABCDEFGH"))
        self.assertEqual(archive.signature, "IWAD")
        self.assertEqual(archive.entries[0].name, "ABCDEFGH")

    def test_empty_archive_allows_directory_zero(self):
        archive = self.open_bytes(header(0, 0))
        self.assertEqual(archive.entries, ())

    def test_zero_size_markers_preserve_all_nonnegative_offset_variants(self):
        # This archive is 28 bytes, with a single directory entry and no payload.
        for offset in (0, 12, 28, 999):
            with self.subTest(offset=offset):
                archive = self.open_bytes(header(1, 12) + directory_entry(offset, 0))
                self.assertEqual(archive.entries[0].offset, offset)
                self.assertEqual(archive.read_lump(0), b"")
                self.assertEqual(list(self.chunks(archive, 0)), [])
                archive.close()

    def test_directory_spanning_chunks_preserves_last_payload(self):
        # One complete 4096-record block and one final record; payload follows.
        directory = directory_entry(0, 0, b"MARKER\0\0") * 4096
        directory += directory_entry(65564, 3, b"LASTDATA")
        archive = self.open_bytes(header(4097, 12) + directory + b"end")
        self.assertEqual(len(archive.entries), 4097)
        self.assertEqual(archive.entries[-1].index, 4096)
        self.assertEqual(archive.entries[-1].name, "LASTDATA")
        self.assertEqual(archive.read_lump(4096), b"end")

    def test_structural_failures(self):
        bad = [b"", b"PWAD", header(0, 0, b"NOPE"), header(-1, 12),
               header(0, -1), header(0, 13), header(1, 0), header(1, 11),
               header(1, 12), header(1, 12) + b"\0" * 15,
               header(1, 12) + directory_entry(-1, 0),
               header(1, 12) + directory_entry(0, -1),
               header(1, 12) + directory_entry(28, 1)]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(self.api.FormatError):
                self.open_bytes(data)
            # A failed parse must release the file, including on Windows.
            self.path.unlink()

    def test_positive_payload_can_overlap_directory(self):
        archive = self.open_bytes(header(1, 12) + directory_entry(12, 4))
        self.assertEqual(archive.read_lump(0), b"\x0c\0\0\0")

    def test_invalid_indexes(self):
        archive = self.open_bytes(original_wad())
        for index in (-1, 3):
            with self.subTest(index=index), self.assertRaises(IndexError):
                archive.read_lump(index)

    def test_limits_are_separate_from_format_errors(self):
        self.assertTrue(issubclass(self.api.FormatError, ValueError))
        self.assertTrue(issubclass(self.api.ResourceLimitError, ValueError))
        self.assertFalse(issubclass(self.api.ResourceLimitError, self.api.FormatError))
        with self.assertRaises(self.api.ResourceLimitError):
            self.open_bytes(original_wad(), max_entries=2)
        archive = self.open_bytes(original_wad(), max_entries=3, max_lump_size=3)
        self.assertEqual(len(archive.entries), 3)
        with self.assertRaises(self.api.ResourceLimitError):
            archive.read_lump(0)
        self.assertEqual(archive.read_lump(2), b"")
        archive.close()
        self.assertEqual(self.open_bytes(original_wad(), max_lump_size=4).read_lump(0), b"ABCD")

    def test_invalid_limits(self):
        for options in ({"max_entries": 0}, {"max_entries": -1}, {"max_lump_size": -1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.open_bytes(header(0, 0), **options)

    def test_close_and_context_exit(self):
        archive = self.open_bytes(original_wad())
        self.assertFalse(archive.closed)
        with archive as entered:
            self.assertIs(entered, archive)
        self.assertTrue(archive.closed)
        archive.close()
        with self.assertRaises(ValueError):
            archive.read_lump(2)
        with self.assertRaises(RuntimeError):
            with self.open_bytes(original_wad()) as another:
                raise RuntimeError("caller failure")
        self.assertTrue(another.closed)

    def test_short_payload_after_file_truncation(self):
        # Directory precedes payload so truncation is observable after parsing.
        archive = self.open_bytes(header(1, 12) + directory_entry(28, 6) + b"abcdef")
        with self.path.open("r+b") as stream:
            stream.truncate(31)
        with self.assertRaises(self.api.FormatError):
            archive.read_lump(0)

    def test_chunked_reads_include_final_partial_chunk(self):
        archive = self.open_bytes(original_wad())
        self.assertEqual(list(self.chunks(archive, 0, chunk_size=3)), [b"ABC", b"D"])
        self.assertEqual(list(self.chunks(archive, 1, chunk_size=2)), [b"CD", b"EF"])
        self.assertEqual(list(self.chunks(archive, 2)), [])

    def test_chunk_reads_are_independent_of_other_reads(self):
        archive = self.open_bytes(original_wad())
        chunks = self.chunks(archive, 0, chunk_size=2)
        self.assertEqual(next(chunks), b"AB")
        self.assertEqual(archive.read_lump(1), b"CDEF")
        self.assertEqual(next(chunks), b"CD")

    def test_chunks_validate_limits_indexes_and_closed_archive(self):
        archive = self.open_bytes(original_wad(), max_lump_size=3)
        with self.assertRaises(self.api.ResourceLimitError):
            list(self.chunks(archive, 0))
        for index in (-1, 3):
            with self.subTest(index=index), self.assertRaises(IndexError):
                list(self.chunks(archive, index))
        for chunk_size in (0, -1):
            with self.subTest(chunk_size=chunk_size), self.assertRaises(ValueError):
                list(self.chunks(archive, 2, chunk_size=chunk_size))
        archive.close()
        with self.assertRaises(ValueError):
            list(self.chunks(archive, 2))

    def test_chunks_detect_truncation_during_iteration(self):
        archive = self.open_bytes(header(1, 12) + directory_entry(28, 6) + b"abcdef")
        chunks = self.chunks(archive, 0, chunk_size=3)
        self.assertEqual(next(chunks), b"abc")
        with self.path.open("r+b") as stream:
            stream.truncate(32)
        with self.assertRaises(self.api.FormatError):
            next(chunks)

    def test_chunks_stop_if_archive_closed_during_iteration(self):
        archive = self.open_bytes(original_wad())
        chunks = self.chunks(archive, 0, chunk_size=2)
        self.assertEqual(next(chunks), b"AB")
        archive.close()
        with self.assertRaises(ValueError):
            next(chunks)

    def test_zero_read_budget_allows_only_markers(self):
        archive = self.open_bytes(original_wad(), max_lump_size=0)
        self.assertEqual(archive.read_lump(2), b"")
        with self.assertRaises(self.api.ResourceLimitError):
            archive.read_lump(0)


if __name__ == "__main__":
    unittest.main()
