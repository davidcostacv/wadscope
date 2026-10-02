# Explain the first findings yourself

This short exercise connects the research to skills you can demonstrate in an interview. Use the exact sample and executable in [target.md](target.md), and check your answers against [findings.md](findings.md).

## 1. Explain an offset using actual bytes

The header starts with `49 57 41 44`. Explain why these bytes are readable as `IWAD`, then decode `5b 0c 00 00` as little-endian. The resulting count is 3,163. Decode `14 9b b6 01` and locate byte 28,744,468 in the sample.

Be able to distinguish a file offset from a virtual address in the executable: `28,744,468` identifies a position in the WAD; `0x140023170` identifies a function location in the analyzed PE memory image.

## 2. Defend the sixteen-byte hypothesis

Explain why a record containing two four-byte fields and an eight-byte name occupies sixteen bytes. Show both the sample arithmetic and the loader's cursor increment at `0x1400232f3`.

Then explain why the loader's forty-byte runtime allocation does not change the file format. Runtime metadata adds information such as file handles and caching state.

## 3. Distinguish evidence from a policy choice

The selected engine has a 4,046-entry PWAD compatibility check. The inspector plan uses a 100,000-entry allocation limit. Explain why these are different constraints and why an archive can be structurally readable while incompatible with a particular engine.

Similarly, the inspector chooses explicit malformed-input checks. Static analysis and source inspection have not demonstrated every engine response to corrupted files.

## 4. Explain duplicate-name behavior without losing information

Locate the backward scan at `0x140023508` in the saved Ghidra project. Explain how a later matching entry can override an earlier resource for engine lookup while both entries still exist in the file.

Describe why selecting an extraction index is less ambiguous than selecting a name. Disclose that the hash-table path's construction order was source-confirmed, and the targeted lookup analysis followed source consultation.

## 5. Demonstrate reproducibility and honest limitations

Show the executable SHA-256 in the target manifest and exported `run.tsv`. Explain the purpose of both: ensuring that addresses and observations refer to the same bytes.

Be ready to explain a real correction: the decompiler displayed an incomplete reader call, so the arguments were checked in assembly. Do not claim that the generated C is the original source, that the investigation was blind, or that these static findings prove all runtime behavior.

The local byte inspector, hashes, and Ghidra exporter run without an LLM or paid API. AI can help formulate questions or review an explanation, but those explanations must be checked against the actual evidence.
