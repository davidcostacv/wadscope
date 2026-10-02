"""Stream a single indexed lump to an explicitly chosen destination."""

import os
import tempfile
from pathlib import Path

from .archive import WadArchive


def extract_lump(archive: WadArchive, index: int,
                 destination: str | os.PathLike[str], overwrite: bool = False) -> Path:
    """Publish a complete payload atomically, preserving prior output on failure.

    Temporary files are siblings of the destination. No-overwrite publication
    requires filesystem hard-link support; no unsafe copy fallback is used.
    Parent directories must already exist. Archive names are never paths.
    """
    output = Path(destination)
    if archive.is_source(output):
        raise ValueError("destination is the source archive")
    if not overwrite and os.path.lexists(output):
        raise FileExistsError(f"destination already exists: {output}")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".wadscope-", suffix=".tmp",
                                         dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            for chunk in archive.iter_lump_chunks(index):
                stream.write(chunk)
        if overwrite:
            os.replace(temporary, output)
        else:
            os.link(temporary, output)
        return output
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
