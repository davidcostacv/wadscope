import importlib
import unittest
import xml.etree.ElementTree as ET

from wadscope.maps import MapGeometry, Vertex, LineDef


NS = '{http://www.w3.org/2000/svg}'


class SvgTests(unittest.TestCase):
    def render(self, geometry):
        try:
            render = importlib.import_module('wadscope.svg').render_svg
        except ModuleNotFoundError:
            self.fail('SVG renderer has not been implemented')
        return render(geometry)

    def test_segments_transform_bounds_and_side_colors(self):
        geometry = MapGeometry(0, 'E1M1', (Vertex(-32, -16), Vertex(32, 48)),
                               (LineDef(0, 1, 1, 0, 0, 0, 65535),
                                LineDef(1, 0, 4, 0, 0, 0, 1)))
        text = self.render(geometry)
        self.assertEqual(text, self.render(geometry))
        root = ET.fromstring(text)
        self.assertEqual(root.get('viewBox'), '-34.56 -50.56 69.12 69.12')
        self.assertEqual(root.get('preserveAspectRatio'), 'xMidYMid meet')
        self.assertEqual(root.get('role'), 'img')
        self.assertEqual(root.get('style'), 'background:#0b1220')
        lines = root.findall('.//' + NS + 'line')
        self.assertEqual(len(lines), 2)
        self.assertEqual([lines[0].get(k) for k in ('x1', 'y1', 'x2', 'y2')],
                         ['-32', '16', '32', '-48'])
        self.assertEqual(lines[0].get('stroke'), '#22d3ee')
        self.assertEqual(lines[1].get('stroke'), '#fbbf24')
        self.assertEqual(lines[0].get('stroke-width'), '0.25')

    def test_empty_point_and_flat_bounds_stay_positive(self):
        for vertices in ((), (Vertex(7, -9),), (Vertex(0, 0), Vertex(1000, 0))):
            root = ET.fromstring(self.render(MapGeometry(0, 'MAP01', vertices, ())))
            bounds = list(map(float, root.get('viewBox').split()))
            self.assertGreater(bounds[2], 0)
            self.assertGreater(bounds[3], 0)
        root = ET.fromstring(self.render(MapGeometry(0, 'MAP01', (), ())))
        self.assertEqual(root.get('viewBox'), '-1 -1 2 2')

    def test_metadata_is_xml_escaped_and_unicode_preserved(self):
        name = '中<&"'
        root = ET.fromstring(self.render(MapGeometry(0, name, (), ())))
        self.assertIn(name, root.find(NS + 'title').text)
        description = root.find(NS + 'desc').text
        self.assertIn('0 vertices', description)
        self.assertIn('0 linedefs', description)
        self.assertEqual(root.findall('.//' + NS + 'script'), [])
