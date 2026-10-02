"""Build original geometry only: this fixture is not a playable DOOM map.

Run from an installed checkout: python examples/create_demo.py
The generated WAD stays in ignored local/; the SVG is safe to redistribute.
"""

import struct
import xml.etree.ElementTree as ET
from pathlib import Path

from wadscope.archive import WadArchive
from wadscope.maps import load_map
from wadscope.svg import render_svg


# Independent hand-designed coordinates: outer gallery, central courtyard,
# four rooms on each side, and openings shown using two-sided side metadata.
# Each tuple is (x1, y1, x2, y2, two_sided).
SEGMENTS = (
    (-384, -256, -48, -256, False), (-48, -256, 48, -256, True),
    (48, -256, 384, -256, False), (384, -256, 384, 256, False),
    (384, 256, 48, 256, False), (48, 256, -48, 256, True),
    (-48, 256, -384, 256, False), (-384, 256, -384, -256, False),
    (-128, -128, -32, -128, False), (-32, -128, 32, -128, True),
    (32, -128, 128, -128, False), (128, -128, 128, -32, False),
    (128, -32, 128, 32, True), (128, 32, 128, 128, False),
    (128, 128, 32, 128, False), (32, 128, -32, 128, True),
    (-32, 128, -128, 128, False), (-128, 128, -128, 32, False),
    (-128, 32, -128, -32, True), (-128, -32, -128, -128, False),
    (-384, -128, -288, -128, False), (-288, -128, -240, -128, True),
    (-240, -128, -192, -128, False), (-192, -128, -192, -256, False),
    (-384, 128, -288, 128, False), (-288, 128, -240, 128, True),
    (-240, 128, -192, 128, False), (-192, 128, -192, 256, False),
    (384, -128, 288, -128, False), (288, -128, 240, -128, True),
    (240, -128, 192, -128, False), (192, -128, 192, -256, False),
    (384, 128, 288, 128, False), (288, 128, 240, 128, True),
    (240, 128, 192, 128, False), (192, 128, 192, 256, False),
    (-384, 0, -288, 0, False), (-288, 0, -240, 0, True),
    (384, 0, 288, 0, False), (288, 0, 240, 0, True),
)


def build_demo() -> bytes:
    """Encode independent on-disk constants without the test fixture helpers."""
    vertices, indices, lines = [], {}, []
    for x1, y1, x2, y2, portal in SEGMENTS:
        endpoints = []
        for point in ((x1, y1), (x2, y2)):
            if point not in indices:
                indices[point] = len(vertices)
                vertices.append(point)
            endpoints.append(indices[point])
        lines.append((*endpoints, 4 if portal else 1, 0, 0, 0, 1 if portal else 65535))
    lumps = ((b'MAP01', b''), (b'THINGS', b''),
             (b'LINEDEFS', b''.join(struct.pack('<7H', *line) for line in lines)),
             (b'SIDEDEFS', b''),
             (b'VERTEXES', b''.join(struct.pack('<hh', *point) for point in vertices)),
             (b'SEGS', b''), (b'SSECTORS', b''), (b'NODES', b''),
             (b'SECTORS', b''), (b'REJECT', b''), (b'BLOCKMAP', b''))
    payload, directory = bytearray(), bytearray()
    for name, data in lumps:
        directory.extend(struct.pack('<ii8s', 12 + len(payload), len(data), name))
        payload.extend(data)
    return struct.pack('<4sii', b'PWAD', len(lumps), 12 + len(payload)) + payload + directory


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    local = root / 'local'
    local.mkdir(exist_ok=True)
    archive_path = local / 'demo-map.wad'
    archive_path.write_bytes(build_demo())
    with WadArchive.open(archive_path) as archive:
        geometry = load_map(archive, 0)
    svg = ET.fromstring(render_svg(geometry))
    svg.find('{http://www.w3.org/2000/svg}title').text = 'WADScope original demo / MAP01'
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.indent(svg, space='  ')
    destination = root / 'examples' / 'map-preview.svg'
    destination.write_text(ET.tostring(svg, encoding='unicode', xml_declaration=True) + '\n',
                           encoding='utf-8', newline='\n')
    print(f'Original geometry: {len(geometry.vertices)} vertices, {len(geometry.lines)} linedefs.')
    print('Created local/demo-map.wad and examples/map-preview.svg (not game-ready).')


if __name__ == '__main__':
    main()
