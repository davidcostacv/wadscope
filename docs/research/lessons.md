# Observed lessons

Only actual mistakes or environment failures are recorded. Each entry includes a prevention check.

## Git owner differs between execution environments

**Observed:** GitHub CLI reported that the checkout was not a Git repository. A direct Git check in the authenticated Windows environment revealed a dubious-ownership failure: the sandbox-created files had a different owner.

**Correction:** Create the remote independently, then push using `git -c safe.directory=<exact checkout path>` for that command. Do not globally trust every repository.

**Prevention:** When the same checkout behaves differently between environments, inspect the direct Git error before retrying GitHub CLI. Scope any ownership exception to the known checkout.

## NUL is not a usable Git excludes file here

**Observed:** `git -c core.excludesFile=NUL status --short` failed with `cannot use NUL as an exclude file`.

**Correction:** `git -c core.excludesFile= status --short` completed successfully.

**Prevention:** Use the verified empty override if the sandbox cannot read the global ignore file. Check individual command exit codes rather than trusting the exit code of a later command in a script.

## Discover launchers before invoking them

**Observed:** The initial environment command invoked `python --version` even though launcher discovery had not found Python on PATH, producing a command-not-found error.

**Correction:** Locate the bundled interpreter and invoke it by absolute path; Python 3.12.14 was confirmed runnable.

**Prevention:** Inspect `Get-Command` results and only invoke discovered executables. A missing PATH launcher is not proof that no runtime exists.

## Pin documentation to the selected release

**Observed:** Ghidra's moving master README requested JDK 25, while the selected 12.1.4 release's README requested JDK 21.

**Correction:** Read the tagged setup documentation before selecting dependencies.

**Prevention:** Record both the software release and its documentation ref. Do not apply requirements from a development branch to a released binary.

## A direct Ghidra JVM launch needs its configured classloader

**Observed:** A direct Java invocation failed before import with `Ghidra class loader not in use`.

**Correction:** Inspect the pinned `support/launch.properties` and include its required `-Djava.system.class.loader=ghidra.GhidraClassLoader` argument. The runner now includes it explicitly.

**Prevention:** Read the installed launch configuration before replacing a wrapper with a direct JVM command.

## A failed Java compilation can leave a stale Ghidra bundle

**Observed:** The sandbox denied a JAR realpath lookup while compiling the exporter. Ghidra left current compiled classes without a generated OSGi manifest. A retry outside the sandbox reused that incomplete cache and could not load the script.

**Correction:** Use new per-run Ghidra settings directories. The third run exported all twenty selected candidates successfully; no old evidence or cache was deleted.

**Prevention:** Preserve failed logs, isolate subsequent settings, and verify `run.tsv` and its executable hash. Ghidra returned exit code zero even when the first export failed, so exit status alone is insufficient.

## Inferred reader arguments can disappear in decompiled C

**Observed:** The loader's decompilation displayed the file reader without several arguments that were plainly passed in registers in the assembly.

**Correction:** Confirm the read offset, buffer, and length in the instructions before documenting behavior.

**Prevention:** Treat inferred signatures as hypotheses. Include instruction addresses whenever arguments affect a format claim.

## Windows redirected streams can use a legacy encoding

**Observed:** Printing a Unicode path to CP1252 output raised UnicodeEncodeError, including after a successful extraction. Argparse also failed while reporting an unknown Unicode command.

**Correction:** Route status, diagnostics, and parser messages through one stream-aware writer. Preserve supported Unicode and escape unsupported characters. Regression tests cover errors, successful publication, argument misuse, and UTF-8 readability.

**Prevention:** Test redirected legacy streams alongside normal UTF-8 output. A filesystem operation and its printed confirmation are separate failure points.
