# Classic map geometry investigation

Recorded 2026-10-02 against the exact Chocolate Doom executable and Freedoom sample hashes in [target.md](target.md). The project proposal already mentioned classic map records. This is a hypothesis-led investigation, not a blind discovery. The geometry instructions below were examined before consulting map-loading engine source. The earlier WAD archive investigation had already consulted `w_wad.c`.

## Byte hypotheses recorded before map source consultation

The Freedoom 0.13.0 `freedoom1.wad` sample starts with marker `E1M1` at directory index 0. Its next marker, `E1M2`, occurs at index 11. Between them are:

| Relative index | Name | Bytes |
| --- | --- | ---: |
| 1 | THINGS | 2,920 |
| 2 | LINEDEFS | 16,450 |
| 3 | SIDEDEFS | 54,870 |
| 4 | VERTEXES | 4,784 |
| 5 | SEGS | 24,684 |
| 6 | SSECTORS | 2,728 |
| 7 | NODES | 19,068 |
| 8 | SECTORS | 4,732 |
| 9 | REJECT | 4,141 |
| 10 | BLOCKMAP | 7,528 |

Four-byte `<2h` vertex records yield 1,196 pairs. The first four are `(2656, 608)`, `(2624, 597)`, `(1784, 1416)`, `(1952, 1184)`, from bytes:

```text
60 0a 60 02 40 0a 55 02 f8 06 88 05 a0 07 a0 04
```

Fourteen-byte `<7H` linedef records yield 1,175 records. The first two are `(0,1,1,0,0,0,65535)` and `(2,3,4,0,0,1,2)`, from bytes:

```text
00 00 01 00 01 00 00 00 00 00 00 00 ff ff
02 00 03 00 04 00 00 00 00 00 01 00 02 00
```

Divisibility and plausible endpoint indexes support the hypotheses; the sample alone cannot establish field names, signedness, dialect compatibility, or malformed-input behavior.

## Binary trace and instruction cross-checks

Local successful runs: `map-research-1`, `map-callers-1`, `map-setup-1`, `map-geometry-1`, using Ghidra 12.1.4 with the saved `x86:LE:64:default`, Windows-compiler project. Generated exports remain ignored under `local/evidence/`; no engine or decompiler source is committed.

`MapEvidence.java` found two string-linked candidates. The `P_LoadThings` diagnostic links to `0x140041750`. The broad `linedefs` diagnostic links to `0x140043d60`; this second candidate does **not** itself establish the on-disk linedef reader. `MapCallers.java` found direct call references from the same containing function, `0x140041f70`, at `0x14004211b` and `0x140042168`. Other references were data, not calls.

The containing function first obtains a marker index through the previously investigated resource lookup wrapper. Assembly sets marker +4 at `0x14004208c` and calls `0x140041100` at `0x14004208f`; marker +2 at `0x1400420a4` calls `0x140041880` at `0x1400420a7`. Marker +1 reaches the things candidate. Other calls use +3, +5, +6, +7, +8, +10, while +9 handles the reject resource. These are positional accesses, not searches for every lump name.

### Vertex candidate `0x140041100`

The resource-length call at `0x140041107` is followed by `SHR RAX,0x2` at `0x140041116`, giving a four-byte record count. Runtime allocation uses eight bytes per record (`0x14004111a`), which is a different representation. The scalar tail reads four bytes at `0x1400411d0`, sign-expands the two words using `PSRAW ...,0xf` and unpacking at `0x1400411d9`–`0x1400411de`, then shifts the resulting dwords by 16 at `0x1400411e2`. The vector loop applies the same operations to several pairs. This supports two signed 16-bit coordinates converted to fixed-point runtime coordinates, not an eight-byte disk record.

### Linedef candidate `0x140041880`

The input cursor advances by `0x0e` at `0x1400419b8`; the runtime cursor separately advances by `0x58`. Count computation uses optimized reciprocal multiplication after reading resource length; the direct input stride is the clearer fourteen-byte evidence.

Endpoint words come from +0 and +2 at `0x1400419e1` and `0x1400419e9` and index the eight-byte runtime vertex array. A dword at input +4 and a word at +8 are copied at `0x1400419cc`–`0x1400419d6`. Input +10 supplies two side words at `0x14004193a`; both are compared with `0xffff` at `0x140041971` and `0x140041994`. The comparisons support an absent-side sentinel. The engine sign-extends endpoint and non-sentinel side words; an inspector's raw unsigned representation must not be described as an exact reproduction of engine indexing.

**Status:** The sample's four/fourteen-byte hypotheses are assembly-cross-checked. No engine execution, gameplay comparison, or malformed-map experiment was performed. The exporter followed explicit selected references; it did not recursively traverse the whole call graph.

## Reproduction

After preparing the pinned target and saved project as described in [target.md](target.md), run from the checkout root in default Windows PowerShell:

```powershell
& '.\scripts\run_ghidra_analysis.ps1' -Mode Refresh -EvidenceName 'map-setup-reproduction' -ScriptName 'MapEvidence.java' -FunctionAddress @('140041f70')
& '.\scripts\run_ghidra_analysis.ps1' -Mode Refresh -EvidenceName 'map-geometry-reproduction' -ScriptName 'MapEvidence.java' -FunctionAddress @('140041100', '140041880')
```

Choose unused evidence names; the runner preserves previous exports. `MapCallers.java` accepts an output directory followed by explicit function entries and records at most 100 direct references per entry. The normal runner deliberately restricts its script-name choices; the one-off caller trace used the same pinned headless toolchain directly.

The [format policy](../format/maps.md) separates the independent inspector's acceptance boundary from the engine observations.

## Pinned source comparison

After recording these instruction observations, the official release tag `chocolate-doom-3.1.1` was resolved to commit `410d96855b5df5410ff591a90efeafa889119224` using the [official tag reference](https://api.github.com/repos/chocolate-doom/chocolate-doom/git/ref/tags/chocolate-doom-3.1.1). The comparison used that exact revision, not the current development branch.

The [disk declarations and marker-relative enum](https://github.com/chocolate-doom/chocolate-doom/blob/410d96855b5df5410ff591a90efeafa889119224/src/doom/doomdata.h#L40-L90) confirm the ten-entry order, two signed coordinate shorts, and seven linedef short slots in the field order used by the format policy. [P_SetupLevel](https://github.com/chocolate-doom/chocolate-doom/blob/410d96855b5df5410ff591a90efeafa889119224/src/doom/p_setup.c#L821-L843), [P_LoadVertexes](https://github.com/chocolate-doom/chocolate-doom/blob/410d96855b5df5410ff591a90efeafa889119224/src/doom/p_setup.c#L120-L149), and [P_LoadLineDefs](https://github.com/chocolate-doom/chocolate-doom/blob/410d96855b5df5410ff591a90efeafa889119224/src/doom/p_setup.c#L423-L485) corroborate the static identification of the setup, vertex, and linedef candidates. Both sides are checked against -1 before dereferencing.

The [SHORT conversion](https://github.com/chocolate-doom/chocolate-doom/blob/410d96855b5df5410ff591a90efeafa889119224/src/i_swap.h#L33) is signed, including for vertex indexes. Consequently, retaining unsigned linedef words and rejecting out-of-range endpoint references are explicitly inspector choices. The stricter record-divisibility checks and unsupported-dialect errors likewise belong to WADScope's policy; they were not demonstrated as engine rejection behavior.

**Final status:** Four/fourteen-byte disk records have sample, assembly, and pinned-source support. Canonical names and field labels have pinned-source confirmation following binary observation. The decoder may now implement the [supported policy](../format/maps.md); unsupported formats and gameplay compatibility remain outside this result.
