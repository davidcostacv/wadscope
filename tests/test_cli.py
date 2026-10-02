import json
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.fixtures import directory_entry, header, original_wad


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "original.wad"
        self.source.write_bytes(original_wad())

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "wadscope", *map(str, args)],
                              capture_output=True, text=True, timeout=10)

    def test_inspect_json(self):
        result = self.run_cli("inspect", self.source, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"signature": "PWAD", "file_size": 70,
                         "directory_offset": 18, "entry_count": 3, "warnings": []})
        self.assertEqual(result.stderr, "")

    def test_list_json_preserves_indexes_and_raw_names(self):
        result = self.run_cli("list", self.source, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = json.loads(result.stdout)
        self.assertEqual(entries[0], {"index": 0, "name": "REPEAT", "raw_name_hex": "5245504541540000",
                                     "offset": 12, "size": 4})
        self.assertEqual(entries[1]["index"], 1)
        self.assertEqual(entries[2]["raw_name_hex"], "4dff005441494c21")

    def test_text_output_escapes_control_names(self):
        self.source.write_bytes(header(1, 12) + directory_entry(999, 0, b"A\n\x1b\t\0\0\0\0"))
        result = self.run_cli("list", self.source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("'A\\n\\x1b\\t'", result.stdout)
        self.assertEqual(len(result.stdout.splitlines()), 1)

    def test_extract_and_marker(self):
        for index, expected in ((1, b"CDEF"), (2, b"")):
            output = self.root / str(index)
            result = self.run_cli("extract", self.source, "--index", index, "--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), expected)
            self.assertIn(str(len(expected)), result.stdout)

    def test_arg_errors_return_two(self):
        cases = [("inspect", self.source, "--max-entries", "0"),
                 ("list", self.source, "--max-lump-size", "-1"),
                 ("extract", self.source, "--index", "-1", "--output", self.root / "out"),
                 ("extract", self.source), (), ("unknown",)]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("usage:", result.stderr)

    def test_operational_failures_return_one_without_tracebacks(self):
        bad = self.root / "bad.wad"
        bad.write_bytes(b"invalid")
        cases = [("inspect", self.root / "missing.wad"), ("inspect", bad),
                 ("inspect", self.source, "--max-entries", 2),
                 ("extract", self.source, "--index", 3, "--output", self.root / "out"),
                 ("extract", self.source, "--index", 0, "--output", self.root / "out", "--max-lump-size", 3),
                 ("extract", self.source, "--index", 0, "--output", self.root / "missing" / "out")]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertTrue(result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_cli_overwrite_requires_flag(self):
        output = self.root / "out"
        output.write_bytes(b"existing")
        args = ("extract", self.source, "--index", 0, "--output", output)
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(output.read_bytes(), b"existing")
        result = self.run_cli(*args, "--overwrite")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes(), b"ABCD")

    def test_compatibility_warning_threshold(self):
        for count in (4046, 4047):
            self.source.write_bytes(header(count, 12) + directory_entry(999, 0) * count)
            result = self.run_cli("inspect", self.source, "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            warnings = json.loads(result.stdout)["warnings"]
            self.assertEqual(len(warnings), int(count > 4046))
            if warnings:
                self.assertIn("4046", warnings[0])

    def test_version_and_help(self):
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0.1.0.dev0", result.stdout)
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("extract", result.stdout)

    def test_legacy_encoding_diagnostic_returns_one(self):
        from wadscope.cli import main
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="cp1252")
        with patch("sys.stderr", stream):
            result = main(["inspect", str(self.root / "中-missing.wad")])
        stream.flush()
        self.assertEqual(result, 1)
        self.assertIn(b"\\u4e2d", buffer.getvalue())
        self.assertNotIn(b"Traceback", buffer.getvalue())

    def test_legacy_encoding_success_status_does_not_fail_after_publish(self):
        from wadscope.cli import main
        output = self.root / "中-output.bin"
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="cp1252")
        with patch("sys.stdout", stream):
            result = main(["extract", str(self.source), "--index", "0", "--output", str(output)])
        stream.flush()
        self.assertEqual(result, 0)
        self.assertEqual(output.read_bytes(), b"ABCD")
        self.assertIn(b"\\u4e2d", buffer.getvalue())

    def test_utf8_status_keeps_readable_unicode(self):
        from wadscope.cli import main
        output = self.root / "中-output.bin"
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="utf-8")
        with patch("sys.stdout", stream):
            result = main(["extract", str(self.source), "--index", "0", "--output", str(output)])
        stream.flush()
        self.assertEqual(result, 0)
        self.assertIn("中".encode(), buffer.getvalue())

    def test_legacy_encoding_argparse_errors_keep_exit_two(self):
        from wadscope.cli import main
        cases = [["中"], ["inspect", str(self.source), "--中"]]
        for args in cases:
            with self.subTest(args=args):
                buffer = io.BytesIO()
                stream = io.TextIOWrapper(buffer, encoding="cp1252")
                with patch("sys.stderr", stream):
                    with self.assertRaises(SystemExit) as caught:
                        main(args)
                stream.flush()
                self.assertEqual(caught.exception.code, 2)
                self.assertIn(b"\\u4e2d", buffer.getvalue())
                self.assertIn(b"usage:", buffer.getvalue())
                self.assertNotIn(b"\n\n", buffer.getvalue())
