"""Measure production directory inspection and streamed extraction separately."""

import argparse
import hashlib
import json
import platform
import statistics
import tempfile
import time
import tracemalloc
from pathlib import Path

from wadscope import WadArchive
from wadscope.extract import extract_lump


def measure(operation, repeats):
    # Allocation tracing changes timings: run the two measurements separately.
    timings = []
    peaks = []
    for _ in range(repeats):
        start = time.perf_counter()
        operation()
        timings.append((time.perf_counter() - start) * 1000)
    for _ in range(repeats):
        tracemalloc.start()
        try:
            operation()
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
    return {"median_ms": statistics.median(timings),
            "median_python_peak_bytes": statistics.median(peaks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--index", required=True, type=int)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")

    def inspect():
        with WadArchive.open(args.file) as archive:
            return len(archive.entries)

    with tempfile.TemporaryDirectory(prefix="wadscope-benchmark-") as directory:
        output = Path(directory) / "selected.bin"

        def extract():
            with WadArchive.open(args.file) as archive:
                extract_lump(archive, args.index, output, overwrite=True)

        # Warm-up plus a byte-range check independent of the extraction API.
        count = inspect()
        extract()
        with WadArchive.open(args.file) as archive:
            entry = archive.entries[args.index]
        expected = hashlib.sha256()
        with args.file.open("rb") as source:
            source.seek(entry.offset)
            remaining = entry.size
            while remaining:
                block = source.read(min(65536, remaining))
                if not block:
                    raise ValueError("short independent source range")
                expected.update(block)
                remaining -= len(block)
        with output.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected.hexdigest() or output.stat().st_size != entry.size:
            raise ValueError("extracted range differs; measurement is invalid")
        with args.file.open("rb") as stream:
            file_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        print(json.dumps({
            "python": platform.python_version(), "platform": platform.platform(),
            "processor": platform.processor(), "file_sha256": file_hash,
            "file_size": args.file.stat().st_size, "entry_count": count,
            "selected_index": args.index, "selected_size": entry.size,
            "selected_sha256": actual, "independent_range_equal": True,
            "repeats_per_measurement": args.repeats,
            "inspect": measure(inspect, args.repeats),
            "extract_including_inspection": measure(extract, args.repeats),
            "scope": "Warm-cache local operations; timing excludes tracing. Python allocations are not process RSS. Extraction uses explicit overwrite of a temporary benchmark output; no fsync guarantee.",
        }, indent=2))


if __name__ == "__main__":
    main()
