"""Deterministic SVG floor-plan previews of validated classic geometry."""

import xml.etree.ElementTree as ET

from .maps import MapGeometry


def _number(value: float) -> str:
    return format(value, '.12g') if value else '0'


def render_svg(geometry: MapGeometry) -> str:
    """Transform world (x, y) to SVG (x, -y); see docs/format/svg.md."""
    if geometry.vertices:
        min_x = min(vertex.x for vertex in geometry.vertices)
        max_x = max(vertex.x for vertex in geometry.vertices)
        min_y = -max(vertex.y for vertex in geometry.vertices)
        max_y = -min(vertex.y for vertex in geometry.vertices)
    else:
        min_x = max_x = min_y = max_y = 0
    extent = max(max_x - min_x, max_y - min_y)
    padding, stroke = max(extent / 25, 1), max(extent / 500, 0.25)
    bounds = (min_x - padding, min_y - padding,
              max_x - min_x + 2 * padding, max_y - min_y + 2 * padding)
    root = ET.Element('svg', {'xmlns': 'http://www.w3.org/2000/svg',
                             'width': '1200', 'height': '800',
                             'viewBox': ' '.join(_number(value) for value in bounds),
                             'preserveAspectRatio': 'xMidYMid meet', 'role': 'img',
                             'style': 'background:#0b1220',
                             'aria-labelledby': 'map-title map-description'})
    ET.SubElement(root, 'title', {'id': 'map-title'}).text = f'WADScope geometry / {geometry.name}'
    ET.SubElement(root, 'desc', {'id': 'map-description'}).text = (
        f'{geometry.name}: {len(geometry.vertices)} vertices, {len(geometry.lines)} linedefs. '
        'Cyan: one-sided; amber: two-sided metadata. Floor-plan preview; '
        'playability and collision are not verified.')
    ET.SubElement(root, 'rect', dict(zip(('x', 'y', 'width', 'height'),
                                       map(_number, bounds)), fill='#0b1220'))
    group = ET.SubElement(root, 'g', {'fill': 'none', 'stroke-linecap': 'round'})
    for line in geometry.lines:
        start, end = geometry.vertices[line.start], geometry.vertices[line.end]
        ET.SubElement(group, 'line', {'x1': str(start.x), 'y1': str(-start.y),
                                     'x2': str(end.x), 'y2': str(-end.y),
                                     'stroke': '#22d3ee' if 65535 in
                                     (line.right_side, line.left_side) else '#fbbf24',
                                     'stroke-width': _number(stroke)})
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='unicode', xml_declaration=True) + '\n'
