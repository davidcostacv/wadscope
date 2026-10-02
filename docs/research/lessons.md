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
