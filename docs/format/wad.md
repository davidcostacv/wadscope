# Initial WAD format and inspector policy

Evidence: [research findings](../research/findings.md), especially F1 and F2. This is the supported model for the archive inspector; map records will be specified after their separate investigation.

## Archive layout

| Header offset | Width | Interpretation |
| --- | --- | --- |
| 0 | 4 bytes | Exact ASCII `IWAD` or `PWAD` |
| 4 | 4 bytes | Signed little-endian 32-bit entry count |
| 8 | 4 bytes | Signed little-endian 32-bit directory offset |

The directory consists of count consecutive sixteen-byte records:

| Record offset | Width | Interpretation |
| --- | --- | --- |
| 0 | 4 bytes | Signed little-endian 32-bit resource offset |
| 4 | 4 bytes | Signed little-endian 32-bit resource size |
| 8 | 8 bytes | Raw name bytes; not necessarily a null-terminated string |

Preserve original name bytes and directory index. Display names terminate at the first NUL and escape undecodable ASCII bytes. Repeated names do not overwrite entries in the inspector. Stored resource ranges may overlap; names and offsets are not unique identifiers.

## Explicit acceptance policy for the first parser

These are WADScope policy choices, not claims that the engine rejects the same inputs:

- Require a complete twelve-byte header and one of the two exact signatures.
- Reject negative counts, negative directory offsets, negative resource sizes, and negative resource offsets.
- Require the directory offset to be within the file; when count is nonzero, require it to be at least twelve so the directory does not start within the header.
- Require `directory_offset + count * 16` to be within the file. Trailing bytes are allowed; end-of-file alignment is not mandatory.
- For positive-size entries, require `offset + size` to be within the file. Allow overlapping ranges, including overlaps with other directory/resource bytes, as long as bounds are valid.
- For zero-size entries, retain the recorded nonnegative offset even when it lies beyond EOF; there are no bytes to read. Reading such an entry returns empty bytes without seeking to that offset. This keeps marker handling separate from nonempty payload validation.
- Accept empty archives with an in-bounds nonnegative directory offset; do not claim the engine's empty-archive behavior is verified.
- Default to at most 100,000 directory entries, with an explicit positive override. This bounds Python object allocations; it is not the engine's PWAD compatibility cap.
- Default to 64 MiB per selected resource read/extraction, with an explicit nonnegative override. Metadata inspection does not load every payload or reject a large payload solely because it will need an override to read.
- Reject negative indexes and out-of-range indexes explicitly. Index selection avoids duplicate-name ambiguity.
- Close owned file handles on failed parsing and context exit. A closed archive cannot read further resources.
- Detect a short payload read, including when the underlying file changes after inspection. Do not claim snapshot consistency for mutable files.

The optional PWAD warning for more than 4,046 entries concerns the selected engine's compatibility, not the archive's structural validity. Case-insensitive eight-byte last-match name lookup is documented engine behavior; it is not required for indexed extraction.

## Evidence boundaries

Sample offsets, count, and stride were checked across both Freedoom WADs and an original byte fixture. Header reads, signature comparisons, and directory stride were checked in the exact executable, then compared with source. Negative inputs, overlapping ranges, and all zero-length offset variants have not been dynamically tested in the engine. They must have independent inspector tests before the parser is declared complete.
