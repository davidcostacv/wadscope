"""Shared complete-file publication with explicit source-alias protection."""

import os
import tempfile
from pathlib import Path
from typing import Iterable

from .archive import WadArchive


def publish_chunks(archive: WadArchive, destination: str | os.PathLike[str],
                   chunks: Iterable[bytes], *, overwrite: bool = False) -> Path:
    """Write sibling temporary data, then publish atomically.

    No-overwrite publication requires filesystem hard-link support. Parent
    directories must already exist; failure preserves any prior destination.
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
            for chunk in chunks:
                stream.write(chunk)
        if overwrite:
            os.replace(temporary, output)
        else:
            os.link(temporary, output)
        return output
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
