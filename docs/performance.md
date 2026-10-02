# Directory inspection measurements

Measured on 2026-10-02 with Python 3.12.14 on Windows 11 build 26300. These are local repeated-open measurements after warm-up, not cold-storage benchmarks or universal speed guarantees. The benchmark measures metadata parsing only; it does not measure payload extraction, rendering, or total process startup.

The original parser issued one unbuffered sixteen-byte directory read per entry. The current parser decodes blocks of at most 64 KiB using `struct.iter_unpack`. Payload reads remain unbuffered to detect file truncation after inspection.

## Reproducible comparison

`scripts/benchmark.py` compares an explicit single-record-I/O reference with the production parser on valid archives. It checks every entry's metadata for equality before timing, records the file hash/environment, and reports medians. The reference includes the same relevant structural checks; it is a benchmark reference, not a second supported parser.

| Workload | Repetitions | Single-record median | Bounded-block median |
| --- | --- | --- | --- |
| Freedoom1, 3,163 entries | 7 | 9.655 ms | 2.202 ms |
| Original 100,000 zero-size markers | 5 | 317.755 ms | 70.652 ms |

Both comparisons returned identical entry metadata. Directory read calls fell from 3,163 to one for the Freedoom sample, and from 100,000 to 25 for the synthetic sample. Batching adds a transient buffer of at most 64 KiB; the entry metadata still requires memory proportional to the entry count. Total peak process memory has not yet been measured.

The synthetic sample is an original 1,600,012-byte PWAD with a directory at offset twelve and repeated zero-size marker records. SHA-256: `52be53f8146049683b2709d229e20255378e407aeff2c15fd7be5facef68b8be`. It is useful for parser stress measurements and exceeds the selected engine's PWAD compatibility cap; it is not a playable demo.

## Windows PowerShell reproduction

After installing WADScope into the local virtual environment, run:

```powershell
.\.venv\Scripts\python.exe '.\scripts\benchmark.py' '.\local\freedoom-0.13.0\freedoom-0.13.0\freedoom1.wad' --repeats 7
```

To construct and benchmark the original stress file from the checkout root:

```powershell
New-Item -ItemType Directory -Path '.\local\evidence' -Force | Out-Null
.\.venv\Scripts\python.exe -c 'import pathlib,struct; p=pathlib.Path("local/evidence/original-100000-markers.wad"); p.write_bytes(struct.pack("<4sii",b"PWAD",100000,12)+struct.pack("<ii8s",0,0,b"MARKER\0\0")*100000)'
.\.venv\Scripts\python.exe '.\scripts\benchmark.py' '.\local\evidence\original-100000-markers.wad' --repeats 5
```

The archive regression suite includes a 4,097-entry fixture to exercise a block boundary and verify the final entry's payload. Performance changes retain the malformed-input, zero-marker, duplicate-name, overlap, and short-read checks. Do not turn the timings above into brittle unit-test thresholds.
