import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from tests.map_fixtures import map_wad, square_lumps


class MapCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'square.wad'
        self.source.write_bytes(map_wad(square_lumps()))
        self.output = self.root / 'map.svg'

    def run_cli(self, *extra, output=None):
        return subprocess.run([sys.executable, '-m', 'wadscope', 'map-svg',
                               str(self.source), '--map-index', '0', '--output',
                               str(self.output if output is None else output), *extra],
                              capture_output=True, text=True, timeout=10)

    def test_svg_export_matches_geometry(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = ET.parse(self.output).findall('.//{http://www.w3.org/2000/svg}line')
        self.assertEqual(len(lines), 4)
        self.assertEqual((lines[0].get('x1'), lines[0].get('y1')), ('-32', '16'))

    def test_existing_output_and_source_alias_preserved(self):
        self.output.write_bytes(b'original')
        self.assertEqual(self.run_cli().returncode, 1)
        self.assertEqual(self.output.read_bytes(), b'original')
        self.assertEqual(self.run_cli('--overwrite').returncode, 0)
        before = self.source.read_bytes()
        self.output.unlink()
        os.link(self.source, self.output)
        self.assertEqual(self.run_cli('--overwrite').returncode, 1)
        self.assertEqual(self.source.read_bytes(), before)

    def test_invalid_limits_and_missing_required_args(self):
        for extra in (('--max-vertices', '0'), ('--max-lines', '-1')):
            self.assertEqual(self.run_cli(*extra).returncode, 2)
        result = subprocess.run([sys.executable, '-m', 'wadscope', 'map-svg', str(self.source)],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)

    def test_geometry_budgets_and_unsupported_dialect_leave_no_output(self):
        for extra in (('--max-vertices', '3'), ('--max-lines', '3'), ('--max-lump-size', '1')):
            self.assertEqual(self.run_cli(*extra).returncode, 1)
            self.assertFalse(self.output.exists())
        self.source.write_bytes(map_wad(square_lumps() + [(b'BEHAVIOR', b'')]))
        self.assertEqual(self.run_cli().returncode, 1)
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_publication_failure_cleans_up(self):
        from wadscope.cli import main
        with patch('os.link', side_effect=OSError('hard links unavailable')):
            self.assertEqual(main(['map-svg', str(self.source), '--map-index', '0',
                                   '--output', str(self.output)]), 1)
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_unicode_destination_on_legacy_stdout_succeeds(self):
        import io
        from wadscope.cli import main
        output = self.root / '中.svg'
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding='cp1252')
        with patch('sys.stdout', stream):
            self.assertEqual(main(['map-svg', str(self.source), '--map-index', '0',
                                   '--output', str(output)]), 0)
        self.assertTrue(output.exists())
