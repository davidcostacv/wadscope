"""Original, independently specified WAD bytes for parser and CLI tests."""

import struct


def header(count, directory_offset, signature=b"PWAD"):
    return struct.pack("<4sii", signature, count, directory_offset)


def directory_entry(offset, size, name=b"DATA\0\0\0\0"):
    if len(name) != 8:
        raise ValueError("fixture names must have eight bytes")
    return struct.pack("<ii8s", offset, size, name)


def original_wad():
    # Header 0..11, payload 12..17, directory 18..65, trailing 66..69.
    return (header(3, 18) + b"ABCDEF"
            + directory_entry(12, 4, b"REPEAT\0\0")
            + directory_entry(14, 4, b"REPEAT\0\0")
            + directory_entry(999, 0, b"M\xff\0TAIL!") + b"TAIL")
