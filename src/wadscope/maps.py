"""Bounded classic geometry decoding; see docs/format/maps.md."""

import re
import struct
from dataclasses import dataclass

from .archive import FormatError, ResourceLimitError, WadArchive


_MARKER = re.compile(rb"(?:E[0-9]M[0-9]|MAP[0-9][0-9])", re.IGNORECASE)
_BLOCK = ("THINGS", "LINEDEFS", "SIDEDEFS", "VERTEXES", "SEGS",
          "SSECTORS", "NODES", "SECTORS", "REJECT", "BLOCKMAP")
_UNSUPPORTED = frozenset(("BEHAVIOR", "TEXTMAP", "ZNODES"))


@dataclass(frozen=True)
class Vertex:
    x: int
    y: int


@dataclass(frozen=True)
class LineDef:
    start: int
    end: int
    flags: int
    special: int
    tag: int
    right_side: int
    left_side: int


@dataclass(frozen=True)
class MapGeometry:
    marker_index: int
    name: str
    vertices: tuple[Vertex, ...]
    lines: tuple[LineDef, ...]


def load_map(archive: WadArchive, marker_index: int, *, max_vertices: int = 100_000,
             max_lines: int = 100_000) -> MapGeometry:
    """Decode only the selected block's vertices and linedefs.

    A valid preview does not certify the other map payloads or playability.
    Duplicate map names remain individually addressable by directory index.
    """
    if archive.closed:
        raise ValueError("archive is closed")
    if type(marker_index) is not int:
        raise TypeError("marker_index must be an integer")
    for name, limit in (("max_vertices", max_vertices), ("max_lines", max_lines)):
        if type(limit) is not int or limit <= 0:
            raise ValueError(f"{name} must be a positive integer")
    entries = archive.entries
    if marker_index < 0 or marker_index >= len(entries):
        raise IndexError(f"map marker index {marker_index} is out of range")
    marker = entries[marker_index]
    if not _MARKER.fullmatch(marker.raw_name.rstrip(b"\0")):
        raise FormatError(f"entry {marker_index} is not a recognized classic map marker")
    if marker.size:
        raise FormatError(f"map marker {marker_index} must have zero length")
    span_end = len(entries)
    for index in range(marker_index + 1, len(entries)):
        entry = entries[index]
        if _MARKER.fullmatch(entry.raw_name.rstrip(b"\0")):
            span_end = index
            break
        if entry.name.upper() in _UNSUPPORTED:
            raise FormatError(f"unsupported map dialect: {entry.name} at entry {index}")
    if marker_index + 11 > span_end:
        raise FormatError(f"map marker {marker_index} has an incomplete classic block")
    for relative, expected in enumerate(_BLOCK, start=1):
        entry = entries[marker_index + relative]
        if entry.name.upper() != expected:
            raise FormatError(f"entry {entry.index}: expected {expected}, found {entry.name!r}")
    vertex_index, line_index = marker_index + 4, marker_index + 2
    vertex_entry, line_entry = entries[vertex_index], entries[line_index]
    for entry, width in ((vertex_entry, 4), (line_entry, 14)):
        if entry.size % width:
            raise FormatError(f"{entry.name} size must be a multiple of {width} bytes")
    vertex_count, line_count = vertex_entry.size // 4, line_entry.size // 14
    for name, count, limit in (("vertices", vertex_count, max_vertices),
                               ("lines", line_count, max_lines)):
        if count > limit:
            raise ResourceLimitError(f"map {name} count {count} exceeds limit {limit}")
    # Both archive read budgets are enforced before allocating geometry objects.
    vertex_bytes = archive.read_lump(vertex_index)
    line_bytes = archive.read_lump(line_index)
    vertices = tuple(Vertex(*values) for values in struct.iter_unpack("<hh", vertex_bytes))
    lines = []
    for index, values in enumerate(struct.iter_unpack("<7H", line_bytes)):
        if values[0] >= vertex_count or values[1] >= vertex_count:
            raise FormatError(f"linedef {index} has an invalid vertex endpoint "
                              f"({values[0]}, {values[1]}); vertex count is {vertex_count}")
        lines.append(LineDef(*values))
    return MapGeometry(marker_index, marker.name, vertices, tuple(lines))
