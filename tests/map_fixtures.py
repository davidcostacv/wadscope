"""Original square geometry; no game assets or engine code."""

import struct

from tests.fixtures import directory_entry, header


def square_lumps(marker=b"E1M1", *, shift=0):
    vertices = b"".join(struct.pack("<hh", x + shift, y) for x, y in
                        ((-32, -16), (32, -16), (32, 48), (-32, 48)))
    lines = b"".join(struct.pack("<7H", a, b, 1, 9, 42, 0, 65535)
                     for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)))
    return [(marker, b""), (b"THINGS", b""), (b"LINEDEFS", lines),
            (b"SIDEDEFS", b""), (b"VERTEXES", vertices), (b"SEGS", b""),
            (b"SSECTORS", b""), (b"NODES", b""), (b"SECTORS", b""),
            (b"REJECT", b""), (b"BLOCKMAP", b"")]


def map_wad(lumps):
    payload = bytearray()
    directory = bytearray()
    for name, data in lumps:
        directory.extend(directory_entry(12 + len(payload), len(data),
                                          name.ljust(8, b"\0")))
        payload.extend(data)
    return header(len(lumps), 12 + len(payload)) + payload + directory
