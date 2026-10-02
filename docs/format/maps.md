# Supported classic map geometry

Evidence and disclosure: [map investigation](../research/maps.md). This policy defines a bounded geometry inspector and preview; it does not reproduce gameplay loading or guarantee engine compatibility.

## Selection and supported block

Select a map by its marker's **directory index**, preserving duplicate markers and repeated resource names. Recognize the raw eight-byte name field only when it contains ASCII `E[0-9]M[0-9]` or `MAP[0-9][0-9]`, case-insensitively, followed entirely by NUL padding. A name with hidden nonzero suffix bytes after its first NUL is not a recognized marker. Require a zero-length selected marker. Its span ends immediately before the next recognized marker, or at directory end. Never retrieve geometry by global last-match resource-name lookup or combine entries across markers.

Require the following ten entries, in this exact consecutive order immediately after the marker:

```text
THINGS LINEDEFS SIDEDEFS VERTEXES SEGS SSECTORS NODES SECTORS REJECT BLOCKMAP
```

Compare their displayed ASCII names case-insensitively. The complete ten-entry block must fit inside the selected span. Trailing entries in the span are allowed, subject to the dialect checks below. Only VERTEXES and LINEDEFS are decoded for the initial preview; the other names establish the supported block, not validated gameplay payloads.

Reject a selected span containing `BEHAVIOR`, `TEXTMAP`, or `ZNODES` with an explicit unsupported-dialect error. This deliberately excludes Hexen-style scripts, UDMF text maps, and extended-node layouts. A structurally valid archive may contain unsupported maps; archive listing and indexed extraction must remain usable. Apply dialect checks within the selected span, not across unrelated maps. These checks are an acceptance policy, not a claim to detect every nonclassic dialect.

## Disk geometry records

| Resource | Width | Fields |
| --- | ---: | --- |
| VERTEXES | 4 bytes | Signed little-endian 16-bit x, y (`<2h`) |
| LINEDEFS | 14 bytes | Seven little-endian 16-bit words (`<7H`): start vertex, end vertex, flags, special, tag, right side, left side |

Preserve linedef words as unsigned raw values, including unknown flags/specials. Side value `0xffff` means no side. Do not interpret it as vertex sentinel: both endpoint indexes must satisfy `index < vertex_count`. Return a clear record-indexed validation error for an invalid endpoint before producing a preview. The engine observed in this investigation uses signed word expansion when indexing; WADScope does not promise gameplay compatibility for large unsigned indexes.

Require resource sizes to be exact multiples of their record widths. Do not silently ignore a trailing partial record. Empty geometry resources may decode to empty collections; a nonempty linedef resource with zero vertices fails endpoint validation. Degenerate lines and repeated vertices remain representable.

## Bounds and preview semantics

Retain the archive reader's default 64 MiB cap for each selected resource. Additionally cap each decoded geometry collection at 100,000 records by default, with an explicit positive override; check counts before reading or allocating record objects. These are tool resource limits, not engine limits. Use only the two selected payloads and do not load unrelated map resources into memory.

Compute bounds from the decoded vertices, keep the coordinate aspect ratio, and invert the display y axis consistently. Draw one segment per linedef using its validated endpoints. Handle empty geometry and zero-width/height extents explicitly so no division by zero occurs. SVG output must contain no embedded source payload, scripts, external resources, or unescaped archive names. The preview is a line drawing of decoded geometry; SIDEDEFS, sectors, BSP nodes, textures, collision, and playability are outside this stage.

A successful parse means this geometry meets WADScope's stated policy. It does not mean every associated lump is valid or that Chocolate Doom accepts the archive.
