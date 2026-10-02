# Research target and environment baseline

Recorded on 2026-10-02. This is a provenance record, not a completed reverse engineering report. The executable has not yet been run or imported into Ghidra.

## Selected engine

- Project: Chocolate Doom.
- Release: `chocolate-doom-3.1.1`.
- [Release page](https://github.com/chocolate-doom/chocolate-doom/releases/tag/chocolate-doom-3.1.1).
- [Windows archive](https://github.com/chocolate-doom/chocolate-doom/releases/download/chocolate-doom-3.1.1/chocolate-doom-3.1.1-win64.zip).
- Archive size reported by the release API: 9,798,661 bytes.
- Archive SHA-256: `58c34c61ae954493fce5ff01fd553898240a0de25658aa97b43ac9510c49581f`.
- This locally computed archive hash matches the release API's asset digest.
- Selected executable: `chocolate-doom.exe`, 875,520 bytes.
- Executable SHA-256: `15e81c194df270fbd71450222e71846247926fabfb889e72e7d855903454d752`.
- PE signature: `50 45 00 00`; machine field: `0x8664` (AMD64).
- COFF symbol count: zero. No PDB was found in the extracted package. Embedded debug information and useful function labels have not been fully inspected; do not claim all symbols are absent.
- [Engine license at the pinned release](https://github.com/chocolate-doom/chocolate-doom/blob/chocolate-doom-3.1.1/COPYING.md): GPL-2.0 as identified by the GitHub license API. Bundled third-party libraries have separate terms. Binaries remain local and are not redistributed by WADScope.

## Selected sample

- Project: Freedoom.
- Release: `v0.13.0`.
- [Release page](https://github.com/freedoom/freedoom/releases/tag/v0.13.0).
- [Asset archive](https://github.com/freedoom/freedoom/releases/download/v0.13.0/freedoom-0.13.0.zip).
- [Published checksum file](https://github.com/freedoom/freedoom/releases/download/v0.13.0/freedoom-0.13.0-CHECKSUM).
- Archive size reported by the release API: 24,143,781 bytes.
- Archive SHA-256: `3f9b264f3e3ce503b4fb7f6bdcb1f419d93c7b546f4df3e874dd878db9688f59`.
- This locally computed archive hash matches the published checksum text. The checksum's PGP signature was not verified; matching hashes are not a claim of signature verification.
- Selected archive resource: `freedoom1.wad`.
- WAD SHA-256: `7323bcc168c5a45ff10749b339960e98314740a734c30d4b9f3337001f9e703d`.
- The extracted `COPYING.txt` contains BSD-style three-clause redistribution conditions and attribution requirements. Keep that file with any redistributed Freedoom-derived content.
- The WAD remains under ignored `local/`; original fixtures will be used for committed examples.

## Environment actually observed

| Component | Observed status |
| --- | --- |
| Git | 2.55.0.windows.3 |
| Python on PATH | Neither `python` nor `py` was found |
| Bundled Python | 3.12.14; executable confirmed runnable through its absolute path |
| Java on PATH | Oracle Java 1.8.0_431, 32-bit client VM |
| Ghidra | Not found in the top-level folders checked; this is not an exhaustive disk inventory |
| Selected Ghidra release | 12.1.4; not downloaded or run yet |
| Pinned Ghidra prerequisite | JDK 21, 64-bit, per the tagged README |

The checked folders were Downloads, Documents, Program Files, and the Projects workspace. The current Java is insufficient for the selected Ghidra release. Use an isolated portable JDK and Ghidra under ignored `local/tools/` rather than replacing system Java. Obtain them from the official vendors and record their hashes and verified versions before analysis.

The bundled interpreter used in this environment is:

```text
C:\Users\David\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

That path is environment-specific; a clean checkout must also work with a separately installed supported Python. No runtime paid API is planned.

## Reproduction in Windows PowerShell

Run from the checkout root. These downloads are explicit pinned releases, not moving `latest` URLs:

```powershell
New-Item -ItemType Directory -Path '.\local\downloads' -Force | Out-Null
Invoke-WebRequest -Uri 'https://github.com/chocolate-doom/chocolate-doom/releases/download/chocolate-doom-3.1.1/chocolate-doom-3.1.1-win64.zip' -OutFile '.\local\downloads\chocolate-doom-3.1.1-win64.zip'
Invoke-WebRequest -Uri 'https://github.com/freedoom/freedoom/releases/download/v0.13.0/freedoom-0.13.0.zip' -OutFile '.\local\downloads\freedoom-0.13.0.zip'
Invoke-WebRequest -Uri 'https://github.com/freedoom/freedoom/releases/download/v0.13.0/freedoom-0.13.0-CHECKSUM' -OutFile '.\local\downloads\freedoom-0.13.0-CHECKSUM'
Get-FileHash -LiteralPath '.\local\downloads\chocolate-doom-3.1.1-win64.zip', '.\local\downloads\freedoom-0.13.0.zip' -Algorithm SHA256
```

Compare both hashes with the exact values above before extraction. For a first extraction into fresh directories:

```powershell
Expand-Archive -LiteralPath '.\local\downloads\chocolate-doom-3.1.1-win64.zip' -DestinationPath '.\local\chocolate-doom-3.1.1'
Expand-Archive -LiteralPath '.\local\downloads\freedoom-0.13.0.zip' -DestinationPath '.\local\freedoom-0.13.0'
Get-FileHash -LiteralPath '.\local\chocolate-doom-3.1.1\chocolate-doom.exe', '.\local\freedoom-0.13.0\freedoom-0.13.0\freedoom1.wad' -Algorithm SHA256
```

The actual setup used `gh release download` for downloading these same URLs, PowerShell for extraction/hashing, and Python's `struct` for reading the PE machine and COFF symbol-count fields. The inspection read the executable as bytes and did not execute it.

## Prior knowledge and source consultation

Before experimentation, the project proposal already described WAD headers, directories, named lumps, offsets, sizes, and map vertices/lines. Therefore the investigation is not blind. Release metadata, upstream licenses, and Ghidra setup documentation were consulted during setup. No Chocolate Doom loader implementation has been consulted as part of this baseline. No hypothesis about engine loading behavior is marked verified here.

## Next research gate

Prepare the pinned Ghidra toolchain, inspect sample bytes, write competing header/directory hypotheses, and import the exact executable. Publish function addresses and experiments before claiming binary-analysis findings or starting the production parser.
