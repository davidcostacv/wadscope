"""Stream a single indexed lump to an explicitly chosen destination."""

import os
from pathlib import Path

from .archive import WadArchive
from .output import publish_chunks


def extract_lump(archive: WadArchive, index: int,
                 destination: str | os.PathLike[str], overwrite: bool = False) -> Path:
    """Publish a complete payload atomically, preserving prior output on failure.

    Temporary files are siblings of the destination. No-overwrite publication
    requires filesystem hard-link support; no unsafe copy fallback is used.
    Parent directories must already exist. Archive names are never paths.
    """
    return publish_chunks(archive, destination, archive.iter_lump_chunks(index),
                          overwrite=overwrite)
