# WAD loader investigation

## Session 1: hypotheses before executable analysis

Recorded on 2026-10-02 against the exact `freedoom1.wad` hash in [target.md](target.md). Engine loading source has not been consulted. Python was used to display raw bytes and compare candidate interpretations; this is not a blind investigation because the project brief already described the broad WAD structure.

### H1 — A 12-byte header with little-endian fields

First twelve observed bytes:

```text
49 57 41 44  5b 0c 00 00  14 9b b6 01
```

Interpretation under test: a four-byte signature, followed by a signed 32-bit entry count and signed 32-bit directory position, little-endian. The sample file is 28,795,076 bytes long. Little-endian interpretation gives 3,163 entries and directory position 28,744,468. Big-endian interpretation gives 1,527,513,088 and 345,748,993; the latter directory position lies outside this sample.

**Status:** Consistent with sample bytes; not yet verified against executable behavior. The sample supports the little-endian hypothesis over this specific big-endian alternative. It does not establish how the engine handles negative fields or other signatures.

### H2 — A directory stride of sixteen bytes

At candidate directory position 28,744,468, the first four candidate records are:

```text
0c 00 00 00 00 00 00 00 45 31 4d 31 00 00 00 00
0c 00 00 00 68 0b 00 00 54 48 49 4e 47 53 00 00
74 0b 00 00 42 40 00 00 4c 49 4e 45 44 45 46 53
b8 4b 00 00 56 d6 00 00 53 49 44 45 44 45 46 53
```

A candidate layout of offset (four bytes), size (four bytes), and name (eight bytes) gives:

| Index | Offset | Size | Name |
| --- | --- | --- | --- |
| 0 | 12 | 0 | E1M1 |
| 1 | 12 | 2,920 | THINGS |
| 2 | 2,932 | 16,450 | LINEDEFS |
| 3 | 19,384 | 54,870 | SIDEDEFS |

The arithmetic `28,744,468 + 3,163 * 16 = 28,795,076` lands exactly at end-of-file. A marker with zero size shares its offset with the next entry. These facts motivate testing zero-length entries and discourage assuming every offset must be unique.

**Status:** Consistent with sample structure; pending executable cross-check and a controlled original fixture. Exact end-of-file alignment is an observation about this sample, not an acceptance rule for every WAD.

### H3 — Resource lookup order is still unknown

Candidate alternatives include first matching name, last matching name, and a prebuilt lookup table with overwrite behavior. Listing a WAD does not distinguish these. Locate name-lookup candidates in the executable, inspect traversal or insertion logic, and later compare with the pinned source. Do not infer lookup order from the directory's stored order alone.

**Status:** Open. The independent inspector will retain entry order and use explicit indexes for extraction regardless of the eventual engine lookup behavior.

## Reproduction of byte observations

The observed values were calculated with Python `struct.unpack_from` over `<4sii`, `<ii8s`, and the competing big-endian header `>4sii`. The sample remained unchanged. The committed `scripts/inspect_wad_bytes.py` repeats the bounded observations and hashes the file without loading the full archive into memory.

The same candidate layout was checked on `freedoom2.wad` (SHA-256 `a8772e088847032510d97ba2312406a6998f21cbab44d4ff10696faa9c0ecd4b`): 28,787,748 bytes, 3,610 entries, directory at 28,729,988, and directory end at EOF. An original 31-byte fixture with a three-byte payload and one entry at offset 15 also produced the independently specified fields. These experiments check the helper and layout consistency; they do not exercise the engine's malformed-file handling.

Example PowerShell command with a supported Python on PATH:

```powershell
python '.\scripts\inspect_wad_bytes.py' '.\local\freedoom-0.13.0\freedoom-0.13.0\freedoom1.wad' --records 4
```

## Session 2: static executable evidence and source comparison

All addresses below refer to the exact executable SHA-256 in [target.md](target.md). Ghidra version 12.1.4, language `x86:LE:64:default`, compiler `windows`. Successful local export runs were `ghidra-run-3` and `ghidra-run-4`. The exporter discovered 33 defined anchor strings and 22 linked functions; only 20 functions were exported per run. Direct string discovery is incomplete by design and does not prove the absence of other functions.

### F1 — Header reads and accepted signatures

The candidate at `0x140023170` references the invalid-signature diagnostic at `0x1400946c8`. Assembly at `0x1400231e4`–`0x1400231f4` passes offset zero, a stack buffer, and length `0x0c` to the file-read wrapper. The subsequent two comparisons use four-byte lengths and the IWAD/PWAD strings. Header count is loaded from stack buffer +4 at `0x140023235`; directory position from buffer +8 at `0x140023260`.

This corroborates H1's twelve-byte structure in a little-endian target. The decompiler initially omits some reader arguments because it inferred an incomplete callee signature; the assembly contains them. That discrepancy is why the decompiled C was not treated as original source.

After this binary observation, the pinned `src/w_wad.c` was consulted. Its packed header declaration and reads match the interpretation, and its byte-order handling confirms the on-disk little-endian fields.

**Status:** Byte-consistent, assembly-cross-checked, and source-confirmed. Error-path behavior has not been exercised dynamically.

### F2 — Directory record size differs from runtime metadata size

At `0x140023256`, the count is shifted left by four to size the directory read. At `0x1400232f3`, the directory cursor advances by `0x10`. At `0x1400232ed`, the name copy length is eight; the preceding/following loads recover the two four-byte fields. This independently corroborates H2's sixteen-byte disk records.

The same function separately allocates runtime entries with size `0x28` at `0x14002327d`. A forty-byte in-memory object is therefore not the disk format's record size. The original sample's zero-length map marker remains evidence that entries need not own distinct, nonempty data ranges.

**Status:** Byte-consistent, assembly-cross-checked, and source-confirmed. Runtime metadata contains additional handles/cache fields that are not needed in the independent inspector.

### F3 — A compatibility limit applies specifically to PWAD

At `0x14002323a`, the candidate compares the header count with `0xfce` (4,046). The PWAD comparison result gates the diagnostic branch at `0x140023406`. The pinned source confirms that this check applies to PWAD rather than all archives.

**Status:** Assembly-cross-checked and source-confirmed. WADScope will report compatibility information separately from structural validity; its chosen resource limits are not an imitation of this engine rule.

### F4 — Name lookup fallback scans backward

The diagnostic wrapper at `0x140023560` calls `0x140023440`. After source consultation, this callee was explicitly exported in run 4. Its no-hash branch at `0x140023508` begins at count minus one; at `0x140023520` it decrements the index. Comparisons are case-insensitive and bounded to eight bytes, with a matching index returned immediately. Thus the fallback favors the last matching entry.

The function also has a hash-table path at `0x140023467`–`0x1400234ef`. The source shows forward construction with insertion at the head of each bucket, consistent with later entries taking priority there too. The hash-table builder has not been separately traced in the executable. H3 is resolved for the observed fallback, while the hash-table ordering remains source-confirmed rather than fully binary-verified.

**Status:** Fallback assembly-cross-checked; source was already consulted before this targeted export. No duplicate-name engine execution experiment was performed. The inspector preserves every entry and uses explicit indexes for extraction.

### Export scope and reproducibility

`scripts/WadEvidence.java` exports defined strings, direct references to string starts, selected function addresses, decompiler output, and up to 300 instructions per function. Undefined strings, references into string interiors, indirect references, and arbitrary call graph traversal are outside its discovery scope. Per-run metadata discloses caps and truncation; both the loader and lookup functions above were exported without instruction truncation.

To reproduce the targeted export from the saved project in PowerShell:

```powershell
& '.\scripts\run_ghidra_analysis.ps1' -Mode Refresh -EvidenceName 'repeat-lookup' -FunctionAddress @('140023440', '140023ab0')
```

The local output includes `run.tsv`, `strings.tsv`, `references.tsv`, `functions.tsv`, logs, and candidate `.c.txt`/`.asm.txt` files. The exact executable hash is embedded in `run.tsv`. Generated decompilation and third-party binaries are kept out of Git; the repository contains original scripts and explanations. Source comparison reference: [pinned loader source](https://github.com/chocolate-doom/chocolate-doom/blob/chocolate-doom-3.1.1/src/w_wad.c), Git blob `1b091834f79daba4a1642c3cd7c18a9382db78d5`.
