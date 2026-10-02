"""Dependency-free command-line WAD inspection and indexed extraction."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .archive import WadArchive
from .extract import extract_lump
from .maps import load_map
from .output import publish_chunks
from .svg import render_svg


def _write_text(message: str, *, file=None) -> None:
    """Keep Unicode readable when supported; escape it on legacy streams."""
    stream = sys.stdout if file is None else file
    encoding = getattr(stream, "encoding", None) or "utf-8"
    printable = message.encode(encoding, errors="backslashreplace").decode(encoding)
    stream.write(printable)


class _ArgumentParser(argparse.ArgumentParser):
    def _print_message(self, message, file=None):
        if message:
            _write_text(message, file=sys.stderr if file is None else file)


def _positive(value: str) -> int:
    number = _nonnegative(value)
    if number == 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def _nonnegative(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a nonnegative integer") from None
    if number < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return number


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="wadscope", description="Inspect and extract DOOM WAD archives.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "list", "extract", "map-svg"):
        subparser = commands.add_parser(command)
        subparser.add_argument("file", type=Path)
        subparser.add_argument("--max-entries", type=_positive, default=100_000)
        subparser.add_argument("--max-lump-size", type=_nonnegative, default=64 * 1024 * 1024)
        if command in ("extract", "map-svg"):
            subparser.add_argument("--index" if command == "extract" else "--map-index",
                                   type=_nonnegative, required=True)
            subparser.add_argument("--output", type=Path, required=True)
            subparser.add_argument("--overwrite", action="store_true")
            if command == "map-svg":
                subparser.add_argument("--max-vertices", type=_positive, default=100_000)
                subparser.add_argument("--max-lines", type=_positive, default=100_000)
        else:
            subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Return 0 for success, 1 for operational failure; argparse uses exit 2."""
    args = _parser().parse_args(argv)
    try:
        with WadArchive.open(args.file, max_entries=args.max_entries,
                             max_lump_size=args.max_lump_size) as archive:
            if args.command == "inspect":
                warnings = []
                if archive.signature == "PWAD" and len(archive.entries) > 4046:
                    warnings.append("PWAD entry count exceeds the vanilla compatibility limit of 4046.")
                summary = {"signature": archive.signature, "file_size": archive.file_size,
                           "directory_offset": archive.directory_offset,
                           "entry_count": len(archive.entries), "warnings": warnings}
                if args.json:
                    print(json.dumps(summary))
                else:
                    print(f"{archive.signature}: {len(archive.entries)} entries, {archive.file_size} bytes, "
                          f"directory at {archive.directory_offset}")
                    for warning in warnings:
                        print(f"Warning: {warning}")
            elif args.command == "list":
                if args.json:
                    # Serialize one record at a time: no second directory-sized
                    # list of dicts or full serialized string is needed.
                    print("[", end="")
                    for entry in archive.entries:
                        if entry.index:
                            print(",", end="")
                        print(json.dumps({"index": entry.index, "name": entry.name,
                                          "raw_name_hex": entry.raw_name.hex(),
                                          "offset": entry.offset, "size": entry.size}), end="")
                    print("]")
                else:
                    for entry in archive.entries:
                        print(f"{entry.index}: {entry.name!r} offset={entry.offset} size={entry.size}")
            elif args.command == "extract":
                destination = extract_lump(archive, args.index, args.output, overwrite=args.overwrite)
                _write_text(f"Extracted {archive.entries[args.index].size} bytes to {str(destination)!r}\n")
            else:
                geometry = load_map(archive, args.map_index, max_vertices=args.max_vertices,
                                    max_lines=args.max_lines)
                svg = render_svg(geometry)
                # Keep the UTF-8 encoding buffer bounded while publishing the
                # required text return value; no second full document copy.
                chunks = (svg[start:start + 16384].encode('utf-8')
                          for start in range(0, len(svg), 16384))
                destination = publish_chunks(archive, args.output, chunks, overwrite=args.overwrite)
                _write_text(f"Rendered {geometry.name}: {len(geometry.vertices)} vertices, "
                            f"{len(geometry.lines)} linedefs to {str(destination)!r}\n")
    except (OSError, ValueError, IndexError) as error:
        _write_text(f"wadscope: {error}\n", file=sys.stderr)
        return 1
    return 0
