"""Bounded byte observations for research; not WADScope's production parser."""

import argparse
import hashlib
import json
import struct
from pathlib import Path


def observe(path: Path, records: int) -> dict:
    file_size = path.stat().st_size
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        stream.seek(0)
        header = stream.read(12)
        if len(header) != 12:
            raise ValueError("The candidate header needs 12 bytes")
        signature, count, offset = struct.unpack("<4sii", header)
        _, big_count, big_offset = struct.unpack(">4sii", header)
        if count < 0 or offset < 0 or offset > file_size:
            raise ValueError("Little-endian candidate fields are outside research bounds")
        end = offset + count * 16
        if end > file_size:
            raise ValueError("Candidate 16-byte directory exceeds file size")
        stream.seek(offset)
        entries = []
        for index in range(min(records, count)):
            raw = stream.read(16)
            position, size, name = struct.unpack("<ii8s", raw)
            entries.append({
                "index": index,
                "directory_record_offset": offset + index * 16,
                "raw_hex": raw.hex(" "),
                "candidate_position": position,
                "candidate_size": size,
                "raw_name_hex": name.hex(" "),
                "candidate_name": name.rstrip(b"\0").decode("ascii", errors="backslashreplace"),
            })
    return {
        "file_size": file_size,
        "sha256": digest,
        "header_hex": header.hex(" "),
        "signature_hex": signature.hex(" "),
        "little_endian_candidate": {"count": count, "directory_offset": offset},
        "big_endian_candidate": {"count": big_count, "directory_offset": big_offset},
        "candidate_directory_end": end,
        "candidate_directory_ends_at_eof": end == file_size,
        "records": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--records", type=int, default=4, choices=range(0, 33), metavar="0..32")
    args = parser.parse_args()
    try:
        print(json.dumps(observe(args.file, args.records), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Observation failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
