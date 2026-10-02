# WADScope portfolio notes

## Demonstrated work

WADScope reconstructs a documented legacy format through a reproducible investigation of a pinned Chocolate Doom executable, independent sample-byte inspection, and later source comparison. The deliverable is an installable Python archive inspector, not a claim to have discovered an unknown format.

The [archive findings](research/findings.md) trace the twelve-byte header, sixteen-byte directory entries, and duplicate-name lookup behavior. The [map investigation](research/maps.md) traces four-byte vertex and fourteen-byte linedef records, including the distinction between disk records and runtime objects. Exact addresses refer to the hashed executable in the [manifest](research/target.md).

The tool implements its own explicit acceptance policy: bounds validation, preserved indexes and raw names, resource budgets, bounded extraction, and source-alias protection. These policies are separately identified from behavior observed in the game engine.

## Current CV wording

> Analyzed Chocolate Doom 3.1.1 WAD loading with Ghidra and built a dependency-free Python tool for archive inspection, indexed extraction, and classic-map SVG export, with malformed-input tests and reproducible binary evidence; validated the installed package on Windows and Linux across Python 3.11, 3.12, and 3.14.

An optional measured-performance sentence:

> Reduced directory read calls through 64 KiB batching, lowering median inspection time from 9.655 ms to 2.202 ms on the recorded Freedoom sample against an equivalent single-record reference.

Use the measurement with its workload and baseline. [Performance notes](performance.md) give the environment, hashes, repetitions, allocation measurements, and limitations. Local runtime requires no AI tokens; optional AI help with explanations does not replace verification.

## Interview explanations

**How was a function identified?** Start with defined error strings and their direct references, then follow explicit caller references and inspect the actual read arguments and cursor advances. Candidate identities gain confidence through independent byte observations and the pinned source comparison.

**How was a hypothesis challenged?** Independently constructed fixtures cover duplicate names, overlapping extents, zero-length markers, block boundaries, truncation, and invalid ranges. Extraction is checked against an independently read source slice, not merely against the parser's own output.

**Why do disk and runtime sizes differ?** The engine converts compact file records into runtime structures. For example, a fourteen-byte linedef is expanded into a much larger object with pointers and derived fields. Treating the runtime stride as the disk width would misparse the archive.

**Why does the inspector differ from the engine?** It exposes raw metadata and applies documented resource and format policies. Engine-specific compatibility caps, signed indexing, and game-loading behavior are distinct from the tool's acceptance rules.

**What was corrected?** An inferred decompiler signature omitted reader arguments that were visible in assembly. Windows redirected CP1252 streams also exposed failures in status and argparse messages; regression tests now cover that failure mode. See [lessons](research/lessons.md).

## Remaining release gates

An actual engine-reference comparison and the 60–90 second video remain release work. Archive inspection, classic geometry decoding, and SVG export are implemented. The original example reproduces exactly with 46 vertices and 40 segments; an independent check matches every segment and color to the builder's original specifications. The Freedoom export has the expected 1,175 SVG segments and selected endpoint coordinates. A development checkpoint should not be presented as completed gameplay rendering or a released v0.1.0. Profile pinning and updates to an external CV or portfolio require the relevant destination.
