"""Bounded WAD parsing from the acceptance policy in docs/format/wad.md."""

import os
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO


class FormatError(ValueError):
    """Archive bytes violate the inspector's structural acceptance policy."""


class ResourceLimitError(ValueError):
    """An operation exceeds a configured resource budget."""


@dataclass(frozen=True)
class WadEntry:
    index: int
    raw_name: bytes
    offset: int
    size: int

    @property
    def name(self) -> str:
        return self.raw_name.split(b"\0", 1)[0].decode("ascii", errors="backslashreplace")


class WadArchive:
    """An owned file handle and immutable directory metadata.

    Reads are not snapshots: changes to the file may raise FormatError. Close
    the archive explicitly or use it as a context manager. No payload is loaded
    while inspecting the directory.
    """

    def __init__(self, stream: BinaryIO, signature: str, file_size: int,
                 directory_offset: int, entries: tuple[WadEntry, ...],
                 max_lump_size: int):
        self._stream = stream
        self.signature = signature
        self.file_size = file_size
        self.directory_offset = directory_offset
        self.entries = entries
        self._max_lump_size = max_lump_size

    @classmethod
    def open(cls, path: str | os.PathLike[str], *, max_entries: int = 100_000,
             max_lump_size: int = 64 * 1024 * 1024) -> "WadArchive":
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        if max_lump_size < 0:
            raise ValueError("max_lump_size must be nonnegative")
        # Unbuffered reads observe truncation after metadata inspection.
        stream = open(path, "rb", buffering=0)
        try:
            file_size = os.fstat(stream.fileno()).st_size
            raw_header = stream.read(12)
            if len(raw_header) != 12:
                raise FormatError("truncated WAD header: expected 12 bytes")
            signature, count, directory_offset = struct.unpack("<4sii", raw_header)
            if signature not in (b"IWAD", b"PWAD"):
                raise FormatError("invalid WAD signature: expected IWAD or PWAD")
            if count < 0 or directory_offset < 0:
                raise FormatError("negative entry count or directory offset")
            if directory_offset > file_size or (count and directory_offset < 12):
                raise FormatError("directory offset is outside the permitted file range")
            if directory_offset + count * 16 > file_size:
                raise FormatError("truncated WAD directory")
            if count > max_entries:
                raise ResourceLimitError(f"entry count {count} exceeds max_entries {max_entries}")
            stream.seek(directory_offset)
            entries = []
            # At most 64 KiB of temporary directory bytes, even with an
            # increased entry cap. Batching avoids one system call per record.
            for first_index in range(0, count, 4096):
                block_size = min(count - first_index, 4096) * 16
                block = stream.read(block_size)
                if len(block) != block_size:
                    raise FormatError(f"truncated directory at entry {first_index}")
                for index, (offset, size, raw_name) in enumerate(
                        struct.iter_unpack("<ii8s", block), start=first_index):
                    if offset < 0 or size < 0:
                        raise FormatError(f"entry {index} has negative offset or size")
                    if size and offset + size > file_size:
                        raise FormatError(f"entry {index} payload extends beyond the file")
                    entries.append(WadEntry(index, raw_name, offset, size))
                del block
            return cls(stream, signature.decode("ascii"), file_size,
                       directory_offset, tuple(entries), max_lump_size)
        except BaseException:
            stream.close()
            raise

    @property
    def closed(self) -> bool:
        return self._stream.closed

    def is_source(self, path: str | os.PathLike[str]) -> bool:
        """Identify existing output aliases without exposing the owned handle."""
        if self.closed:
            raise ValueError("archive is closed")
        try:
            candidate = os.stat(path)
        except FileNotFoundError:
            return False
        return os.path.samestat(candidate, os.fstat(self._stream.fileno()))

    def _selected_entry(self, index: int) -> WadEntry:
        if self.closed:
            raise ValueError("archive is closed")
        if index < 0 or index >= len(self.entries):
            raise IndexError(f"lump index {index} is out of range")
        entry = self.entries[index]
        if entry.size > self._max_lump_size:
            raise ResourceLimitError(
                f"entry {index} size {entry.size} exceeds max_lump_size {self._max_lump_size}")
        return entry

    def read_lump(self, index: int) -> bytes:
        entry = self._selected_entry(index)
        if entry.size == 0:
            return b""
        self._stream.seek(entry.offset)
        data = self._stream.read(entry.size)
        if len(data) != entry.size:
            raise FormatError(f"short payload read for entry {index}")
        return data

    def iter_lump_chunks(self, index: int, chunk_size: int = 65536) -> Iterator[bytes]:
        """Yield at most chunk_size bytes at a time, enforcing the read budget.

        Validation occurs when iteration starts. A seek for each chunk lets
        callers interleave indexed reads between yields on this archive.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        entry = self._selected_entry(index)
        position = entry.offset
        remaining = entry.size
        while remaining:
            if self.closed:
                raise ValueError("archive is closed")
            size = min(remaining, chunk_size)
            self._stream.seek(position)
            data = self._stream.read(size)
            if len(data) != size:
                raise FormatError(f"short payload read for entry {index}")
            position += size
            remaining -= size
            yield data

    def close(self) -> None:
        self._stream.close()

    def __enter__(self) -> "WadArchive":
        if self.closed:
            raise ValueError("archive is closed")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
