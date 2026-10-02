# WADScope

**From raw bytes to playable worlds: investigating DOOM's WAD loader and building an independent archive inspector.**

WADScope is a reverse engineering project with two connected deliverables: an evidence-based study of how a compiled DOOM engine loads WAD files, and a Python tool that implements the recovered behavior. The planned visual output is an SVG floor plan reconstructed from a level's geometry.

> **Status: project kickoff.** This repository currently contains the project brief and roadmap. The parser, CLI, SVG exporter, automated tests, and binary analysis report have not been implemented yet.

## The research question

How does a compiled engine interpret a WAD archive, and which parts of that behavior can be independently reconstructed, explained, and tested?

The analysis target will be a pinned build of [Chocolate Doom](https://github.com/chocolate-doom/chocolate-doom). Demonstration assets will come from [Freedoom](https://github.com/freedoom/freedoom) or small original fixtures.

WAD is an established, documented format, and Chocolate Doom is open source. This project is an independent reconstruction and validation exercise. Its contribution will be the investigation trail, implementation, and reproducible evidence—not a claim to have discovered an unknown format.

## What the first release will do

| Planned capability | Purpose |
| --- | --- |
| Inspect archive metadata and directory entries | Connect byte-level structure to named resources, commonly called lumps |
| List lump names, offsets, and sizes | Make the inferred layout inspectable |
| Validate archive structure | Report truncated data and out-of-bounds references clearly |
| Extract a selected lump | Verify recovered byte ranges against the original file |
| Export a classic DOOM-format map to SVG | Turn recovered vertices and lines into a visible result |

The first release will focus on classic DOOM-format archives and map geometry. Editing archives, rendering a complete game, supporting every WAD dialect, and implementing a 3D viewer are outside its initial scope. Format acceptance rules will distinguish legal edge cases from invalid inputs rather than assuming every unusual archive is corrupt.

## Investigation workflow

1. **Pin the target.** Record the engine version or commit, binary SHA-256, architecture, build origin, tool versions, and sample provenance. Keep symbol availability explicit.
2. **Observe the bytes.** Compare sample archives, annotate candidate fields, and write hypotheses before consulting the format implementation.
3. **Inspect the executable.** Use Ghidra to locate archive-loading behavior through strings, cross-references, control flow, and data access. Check decompiler output against assembly where the distinction matters.
4. **Implement the model.** Build an independent Python parser from the observations. Record uncertain behavior instead of silently inventing rules.
5. **Challenge the model.** Exercise valid files, deliberately malformed fixtures, and legal boundary cases. Compare extraction results with the corresponding source byte ranges.
6. **Validate against source.** Compare findings with the pinned Chocolate Doom source and external documentation. Record agreements, corrections, and unresolved questions.

Any source code or documentation consulted before a finding will be disclosed. AI-assisted code or notes will be reviewed and verified; they will not be presented as experimental evidence.

## Evidence standard

Each important finding should include:

- A concrete claim and its confidence level.
- A sample identifier, hash, and relevant byte offsets.
- The target function or instruction location, tied to the exact binary.
- A short explanation of the observed data flow.
- A reproducible experiment or test.
- A note stating whether the claim is inferred, experimentally verified, or source-confirmed.

For example, an entry-size hypothesis should be supported by annotated archive bytes, the loader's access pattern, and fixtures that distinguish it from competing interpretations. Screenshots will illustrate findings; written evidence and reproducible steps will carry the explanation.

## Roadmap

See the [implementation plan](docs/superpowers/plans/2026-10-02-wadscope.md) for task checklists, verification gates, Windows PowerShell commands, cost controls, and portfolio deliverables.

- [x] Define the research question, scope, and repository brief.
- [ ] **Milestone 1 — First evidence:** pin the target and sample; investigate the archive header and directory; publish the first annotated finding.
- [ ] **Milestone 2 — Archive inspector:** implement metadata listing, bounds validation, and selected-lump extraction with focused tests.
- [ ] **Milestone 3 — Visible reconstruction:** decode classic map vertices and lines; export an SVG and verify it against a reference view.
- [ ] **Milestone 4 — Reproducible release:** publish installation steps, CLI examples, automated checks, a concise research report, and a 60–90 second demo.

An optional later milestone is a Ghidra script that automates a specific, validated analysis step. Automation will follow the manual investigation.

## Planned repository layout

The following layout is a design target; these directories do not exist yet:

```text
src/wadscope/       Independent parser, validation, extraction, and CLI
tests/             Original fixtures and regression tests
docs/research/     Hypotheses, experiments, findings, and source comparisons
docs/format/       Reconstructed format notes with evidence references
scripts/           Reproduction helpers and optional Ghidra automation
examples/          Small original samples and generated SVG output
```

## Tools and prerequisites

- **Python 3:** binary file handling, `struct`, exceptions, and testable functions.
- **Ghidra:** static analysis, cross-references, function annotation, and decompilation.
- **A hex viewer:** inspection of actual file contents and offsets.
- **Git:** versioned code, research notes, and reproducible checkpoints.
- **Basic C and assembly literacy:** structures, pointers, byte order, and memory access.

Windows is a suitable starting environment. The exact analysis setup and dependency versions will be recorded when the target build is selected. Installation and usage commands will be added once a working tool exists.

## Validation and release criteria

The first release is ready when a reader can reproduce the documented investigation and use the inspector on the supported samples.

- Valid sample archives produce the expected metadata and extracted bytes.
- Truncated headers, incomplete directories, and out-of-bounds entries produce explicit errors.
- Legal edge cases, including zero-length entries and repeated names, have documented behavior and tests.
- Extraction does not turn archive-provided names into unsafe filesystem paths.
- Resource limits and unsupported formats are documented.
- The SVG geometry is compared with a reference map view, with known rendering limitations stated.
- Automated checks run on the declared supported environment.
- A release includes working commands, sample provenance, actual results, and an honest limitations section.

## Portfolio deliverables

The completed project should let a reviewer understand the result quickly and inspect the reasoning deeply:

1. A short demo showing archive inspection, extraction, and SVG export.
2. A research report tracing findings from bytes and disassembly to verified behavior.
3. A usable, tested tool with a reproducible setup.
4. A discussion of mistakes, corrected hypotheses, and remaining limitations.

Benchmarks, coverage figures, and CV claims will only be published after they have been measured or demonstrated.

## References and asset policy

- [Chocolate Doom](https://github.com/chocolate-doom/chocolate-doom): engine analysis target and eventual source-validation reference.
- [Freedoom](https://github.com/freedoom/freedoom): freely licensed demonstration assets; preserve its copyright notices and license when redistributing content.
- [Ghidra](https://github.com/NationalSecurityAgency/ghidra): reverse engineering framework.

Commercial game assets and third-party binaries are not included. Any future third-party sample will carry its provenance and applicable license. WADScope's license applies to original repository content; it does not replace upstream licenses. Upstream source excerpts, if needed, will be attributed and handled under their own license terms.

## License

Original WADScope content is released under the [MIT License](LICENSE).
