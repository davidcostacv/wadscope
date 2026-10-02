"""Behavioral coverage of the bounded classic map selection policy."""

import importlib
import struct
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from wadscope.archive import FormatError, ResourceLimitError, WadArchive
from tests.map_fixtures import map_wad, square_lumps


class MapTests(unittest.TestCase):
    def setUp(self):
        try:
            self.maps = importlib.import_module("wadscope.maps")
        except ModuleNotFoundError:
            self.fail("classic map decoder is not implemented")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "square.wad"

    def archive(self, lumps=None, **options):
        self.path.write_bytes(map_wad(square_lumps() if lumps is None else lumps))
        archive = WadArchive.open(self.path, **options)
        self.addCleanup(archive.close)
        return archive

    def test_square_coordinates_records_and_immutability(self):
        result = self.maps.load_map(self.archive(), 0)
        self.assertEqual((result.marker_index, result.name), (0, "E1M1"))
        self.assertEqual(result.vertices, tuple(self.maps.Vertex(x, y) for x, y in
                         ((-32, -16), (32, -16), (32, 48), (-32, 48))))
        self.assertEqual(result.lines[3], self.maps.LineDef(3, 0, 1, 9, 42, 0, 65535))
        with self.assertRaises(FrozenInstanceError):
            result.vertices[0].x = 10

    def test_adjacent_maps_use_selected_index_even_with_duplicate_names(self):
        archive = self.archive(square_lumps() + square_lumps(shift=100))
        self.assertEqual(self.maps.load_map(archive, 11).vertices[0].x, 68)
        self.assertEqual(self.maps.load_map(archive, 0).vertices[0].x, -32)

    def test_case_insensitive_names(self):
        result = self.maps.load_map(self.archive([(name.lower(), data) for name, data
                                                  in square_lumps(b"MAP01")]), 0)
        self.assertEqual(result.name, "map01")

    def test_strict_marker_names(self):
        for name in (b"E12M1", b"MAP1", b"E1M1\0X", b"EAM1", b"MAP001", b"XMAP01"):
            with self.subTest(name=name), self.assertRaises(FormatError):
                self.maps.load_map(self.archive(square_lumps(name)), 0)

    def test_marker_must_be_empty(self):
        lumps = square_lumps()
        lumps[0] = (b"E1M1", b"x")
        with self.assertRaises(FormatError):
            self.maps.load_map(self.archive(lumps), 0)

    def test_invalid_marker_index(self):
        archive = self.archive()
        for index in (-1, 11, True, 0.0, "0"):
            with self.subTest(index=index), self.assertRaises((IndexError, ValueError, TypeError)):
                self.maps.load_map(archive, index)
        with self.assertRaises(FormatError):
            self.maps.load_map(archive, 4)

    def test_missing_block_cannot_borrow_from_next_map(self):
        with self.assertRaises(FormatError):
            self.maps.load_map(self.archive(square_lumps()[:4] + square_lumps(b"MAP01")), 0)

    def test_reordered_missing_or_duplicate_required_names(self):
        for operation in ("swap", "missing", "duplicate"):
            lumps = square_lumps()
            if operation == "swap":
                lumps[2], lumps[4] = lumps[4], lumps[2]
            elif operation == "missing":
                del lumps[4]
            else:
                lumps.insert(4, lumps[2])
            with self.subTest(operation=operation), self.assertRaises(FormatError):
                self.maps.load_map(self.archive(lumps), 0)

    def test_dialect_resources_rejected_anywhere_in_selected_span(self):
        for name in (b"BEHAVIOR", b"TEXTMAP", b"ZNODES"):
            with self.subTest(name=name), self.assertRaisesRegex(FormatError, "unsupported.*dialect"):
                self.maps.load_map(self.archive(square_lumps() + [(name.lower(), b"")]), 0)

    def test_dialect_in_other_map_does_not_reject_selected_map(self):
        archive = self.archive(square_lumps() + square_lumps(b"MAP01") + [(b"TEXTMAP", b"")])
        self.assertEqual(len(self.maps.load_map(archive, 0).lines), 4)

    def test_trailing_extensions_and_unrelated_payloads_are_not_read(self):
        lumps = square_lumps() + [(b"CUSTOM", b"x" * 100)]
        lumps[1] = (b"THINGS", b"x" * 100)
        result = self.maps.load_map(self.archive(lumps, max_lump_size=56), 0)
        self.assertEqual(len(result.lines), 4)

    def test_geometry_record_remainders(self):
        for index in (2, 4):
            lumps = square_lumps()
            name, data = lumps[index]
            lumps[index] = (name, data + b"x")
            with self.subTest(index=index), self.assertRaisesRegex(FormatError, "multiple"):
                self.maps.load_map(self.archive(lumps), 0)

    def test_invalid_endpoint_reports_record(self):
        for endpoint in (4, 65535):
            lumps = square_lumps()
            data = bytearray(lumps[2][1])
            struct.pack_into("<H", data, 14 + 2, endpoint)
            lumps[2] = (b"LINEDEFS", bytes(data))
            with self.subTest(endpoint=endpoint), self.assertRaisesRegex(FormatError, "linedef 1"):
                self.maps.load_map(self.archive(lumps), 0)

    def test_empty_geometry(self):
        lumps = square_lumps()
        lumps[2] = (b"LINEDEFS", b"")
        lumps[4] = (b"VERTEXES", b"")
        result = self.maps.load_map(self.archive(lumps), 0)
        self.assertEqual((result.vertices, result.lines), ((), ()))

    def test_lines_with_no_vertices_fail(self):
        lumps = square_lumps()
        lumps[4] = (b"VERTEXES", b"")
        with self.assertRaisesRegex(FormatError, "linedef 0"):
            self.maps.load_map(self.archive(lumps), 0)

    def test_record_limits_checked_before_reading_payloads(self):
        for options in ({"max_vertices": 3}, {"max_lines": 3}):
            archive = self.archive()
            # Remove payloads after directory parsing: a read would fail first.
            with self.path.open("r+b") as stream:
                stream.truncate(12)
            with self.subTest(options=options), self.assertRaises(ResourceLimitError):
                self.maps.load_map(archive, 0, **options)
            archive.close()

    def test_limits_require_positive_integers(self):
        archive = self.archive()
        for key in ("max_vertices", "max_lines"):
            for value in (0, -1, True, 1.5):
                with self.subTest(key=key, value=value), self.assertRaises((TypeError, ValueError)):
                    self.maps.load_map(archive, 0, **{key: value})
        self.assertEqual(len(self.maps.load_map(archive, 0, max_vertices=4, max_lines=4).lines), 4)

    def test_archive_payload_budget_is_preserved(self):
        with self.assertRaises(ResourceLimitError):
            self.maps.load_map(self.archive(max_lump_size=55), 0)

    def test_closed_archive(self):
        archive = self.archive()
        archive.close()
        with self.assertRaisesRegex(ValueError, "closed"):
            self.maps.load_map(archive, 0)


if __name__ == "__main__":
    unittest.main()
