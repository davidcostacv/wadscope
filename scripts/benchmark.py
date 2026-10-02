"""Measure valid-directory decoding with single-record versus bounded-block I/O."""

import argparse
import hashlib
import json
import platform
import statistics
import struct
import time
from pathlib import Path

from wadscope import FormatError, WadArchive, WadEntry


def single_record_baseline(path: Path) -> tuple[WadEntry, ...]:
    """Explicit reference for valid input; same checks and default entry budget."""
    file_size = path.stat().st_size
    with path.open("rb", buffering=0) as stream:
        header = stream.read(12)
        if len(header) != 12:
            raise FormatError("truncated header")
        signature, count, offset = struct.unpack("<4sii", header)
        if signature not in (b"IWAD", b"PWAD") or count < 0 or offset < 0:
            raise FormatError("invalid header")
        if offset > file_size or (count and offset < 12) or offset + count * 16 > file_size:
            raise FormatError("invalid directory bounds")
        if count > 100_000:
            raise ValueError("benchmark default budget is 100000 entries")
        stream.seek(offset)
        entries = []
        for index in range(count):
            row = stream.read(16)
            if len(row) != 16:
                raise FormatError("short directory record")
            position, size, name = struct.unpack("<ii8s", row)
            if position < 0 or size < 0 or (size and position + size > file_size):
                raise FormatError("invalid resource extent")
            entries.append(WadEntry(index, name, position, size))
        return tuple(entries)


def production(path: Path) -> tuple[WadEntry, ...]:
    with WadArchive.open(path) as archive:
        return archive.entries


def median_ms(operation, path, repeats):
    elapsed = []
    for _ in range(repeats):
        start = time.perf_counter()
        result = operation(path)
        elapsed.append((time.perf_counter() - start) * 1000)
        del result
    return statistics.median(elapsed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--repeats", type=int, default=7)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    baseline_entries = single_record_baseline(args.file)
    production_entries = production(args.file)
    if baseline_entries != production_entries:
        raise ValueError("Metadata differs; timing comparison is invalid")
    count = len(production_entries)
    del baseline_entries, production_entries
    with args.file.open("rb") as stream:
        sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    print(json.dumps({
        "python": platform.python_version(),
        "platform": platform.platform(),
        "file_sha256": sha256,
        "file_size": args.file.stat().st_size,
        "entry_count": count,
        "repeats": args.repeats,
        "metadata_equal": True,
        "single_record_median_ms": median_ms(single_record_baseline, args.file, args.repeats),
        "bounded_block_median_ms": median_ms(production, args.file, args.repeats),
        "scope": "Repeated local opens after warm-up; directory inspection only, not extraction or cold-cache I/O",
    }, indent=2))


if __name__ == "__main__":
    main()
