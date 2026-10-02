# Research target and environment baseline

Recorded on 2026-10-02. This is a provenance record, not a completed reverse engineering report. The executable has been imported and statically analyzed in Ghidra; it has not been executed as a game. Initial findings are recorded in [findings.md](findings.md).

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
| Selected Ghidra release | 12.1.4; downloaded, hashed, and run headlessly |
| Pinned Ghidra prerequisite | JDK 21, 64-bit, per the tagged README |
| Portable JDK actually used | Temurin 21.0.12.1+1, 64-bit, verified with `java -version` |

The checked folders were Downloads, Documents, Program Files, and the Projects workspace. The system Java is insufficient for the selected Ghidra release. Portable tools were extracted under ignored `local/tools/`; system Java and PATH were not modified.

### Pinned tool archives

| Tool | Release archive | SHA-256 |
| --- | --- | --- |
| Ghidra 12.1.4 | `ghidra_12.1.4_PUBLIC_20260921.zip` | `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db` |
| Temurin JDK 21.0.12.1+1 | `OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip` | `f9d6e191ab098c0d416e7d588a24420a8621cd2f4720dab2459b8b7b2d2d8b4e` |

Both local hashes matched their release API asset digests. Sources: [Ghidra release](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build), [Temurin release](https://github.com/adoptium/temurin21-binaries/releases/tag/jdk-21.0.12.1%2B1), and [Ghidra's tagged prerequisites](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.1.4_build/README.md).

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

Before experimentation, the project proposal already described WAD headers, directories, named lumps, offsets, sizes, and map vertices/lines. Therefore the investigation is not blind. Release metadata, upstream licenses, and Ghidra setup documentation were consulted during setup. After byte observations and the first successful candidate-function export, `src/w_wad.c` at `chocolate-doom-3.1.1` was consulted to validate the header/directory interpretations. Its Git blob is `1b091834f79daba4a1642c3cd7c18a9382db78d5`. The later targeted name-lookup export therefore follows source consultation; do not present its interpretation as a blind discovery.

## Toolchain and analysis reproduction

Download the pinned tool ZIPs into `local/downloads`, compare their hashes above, and extract them into `local/tools`. For a fresh checkout, these PowerShell commands obtain the exact releases:

```powershell
Invoke-WebRequest -Uri 'https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip' -OutFile '.\local\downloads\ghidra_12.1.4_PUBLIC_20260921.zip'
Invoke-WebRequest -Uri 'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip' -OutFile '.\local\downloads\OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip'
Get-FileHash -LiteralPath '.\local\downloads\ghidra_12.1.4_PUBLIC_20260921.zip', '.\local\downloads\OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip' -Algorithm SHA256
```

After verifying those hashes:

```powershell
Expand-Archive -LiteralPath '.\local\downloads\ghidra_12.1.4_PUBLIC_20260921.zip' -DestinationPath '.\local\tools'
Expand-Archive -LiteralPath '.\local\downloads\OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip' -DestinationPath '.\local\tools'
& '.\scripts\run_ghidra_analysis.ps1' -Mode Import -EvidenceName 'first-import'
& '.\scripts\run_ghidra_analysis.ps1' -Mode Refresh -EvidenceName 'lookup-export' -FunctionAddress @('140023440', '140023ab0')
```

Use fresh extraction destinations, or skip extraction for already verified installations. The runner gives each export new settings to avoid incomplete OSGi bundle caches, validates the target hash, and checks a newly produced manifest rather than trusting Ghidra's exit code alone. It refuses to overwrite an evidence directory. Windows execution policy may require a process-scoped exception to run a reviewed local script; no global policy changes are required.

Actual initial import: language `x86:LE:64:default`, compiler spec `windows`, default analyzers, maximum two CPUs, 180-second per-file timeout. Ghidra reported analysis success in 39 seconds. The MinGW pseudo-relocation analyzer reported a missing list, and the Windows resource-reference analyzer failed to compile its script in the sandbox. These are limitations of that initial analysis, not evidence that every analyzer completed. Exports `ghidra-run-3` and `ghidra-run-4` completed outside the sandbox using the saved project, with all 20 selected functions decompiled in each run. Full project and generated decompiler output remain local.

## Current research gate

Header and directory layout now have byte, assembly, and source cross-checks. The [format notes](../format/wad.md) define an initial inspector acceptance policy. Name lookup has a checked binary fallback branch and a source-confirmed hash-table description; the hash-table builder has not yet been independently traced. None of these claims is a dynamic gameplay experiment.
