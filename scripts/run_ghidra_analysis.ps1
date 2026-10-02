# Run static analysis with the pinned portable toolchain; never execute the target.
[CmdletBinding()]
param(
    [ValidateSet('Import', 'Refresh')]
    [string]$Mode = 'Import',
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')]
    [string]$EvidenceName = 'ghidra-reproduction',
    [ValidateSet('WadEvidence.java', 'MapEvidence.java')]
    [string]$ScriptName = 'WadEvidence.java',
    [ValidateCount(0, 20)]
    [ValidatePattern('^[0-9A-Fa-f]{8,16}$')]
    [string[]]$FunctionAddress = @()
)

$ErrorActionPreference = 'Stop'
$researchRoot = Split-Path -Parent $PSScriptRoot
$javaPath = Join-Path $researchRoot 'local\tools\jdk-21.0.12.1+1\bin\java.exe'
$utilityJar = Join-Path $researchRoot 'local\tools\ghidra_12.1.4_PUBLIC\Ghidra\Framework\Utility\lib\Utility.jar'
$targetPath = Join-Path $researchRoot 'local\chocolate-doom-3.1.1\chocolate-doom.exe'
$projectDirectory = Join-Path $researchRoot 'local\ghidra-projects'
$projectFile = Join-Path $projectDirectory 'WADScope.gpr'
$outputDirectory = Join-Path $researchRoot "local\evidence\$EvidenceName"
$expectedHash = '15E81C194DF270FBD71450222E71846247926FABFB889E72E7D855903454D752'

foreach ($requiredPath in @($javaPath, $utilityJar, $targetPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Missing prerequisite: $requiredPath. Follow docs/research/target.md."
    }
}
if ((Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash -ne $expectedHash) {
    throw 'Target hash does not match the recorded research executable.'
}
if (Test-Path -LiteralPath $outputDirectory) {
    throw 'Evidence directory already exists. Choose a new -EvidenceName to preserve previous output.'
}
if ($Mode -eq 'Import' -and (Test-Path -LiteralPath $projectFile)) {
    throw 'Project already exists. Use -Mode Refresh to export from the saved analysis.'
}
if ($Mode -eq 'Refresh' -and -not (Test-Path -LiteralPath $projectFile)) {
    throw 'No saved project exists. Use -Mode Import first.'
}

foreach ($directory in @($projectDirectory, $outputDirectory,
        (Join-Path $outputDirectory 'settings'),
        (Join-Path $researchRoot 'local\cache'),
        (Join-Path $researchRoot 'local\temp'))) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}

$javaArguments = @(
    '-Xmx2G', '-Xshare:off', '--enable-native-access=ALL-UNNAMED',
    '-Djava.system.class.loader=ghidra.GhidraClassLoader',
    '-Dfile.encoding=UTF8', '-Duser.language=en', '-Duser.country=US',
    "-Dapplication.settingsdir=$outputDirectory\settings",
    "-Dapplication.cachedir=$researchRoot\local\cache",
    "-Dapplication.tempdir=$researchRoot\local\temp",
    '-cp', $utilityJar, 'ghidra.Ghidra', 'ghidra.app.util.headless.AnalyzeHeadless'
)
$headlessArguments = @($projectDirectory, 'WADScope')
if ($Mode -eq 'Import') {
    $headlessArguments += @('-import', $targetPath, '-max-cpu', '2', '-analysisTimeoutPerFile', '180')
} else {
    $headlessArguments += @('-process', 'chocolate-doom.exe', '-noanalysis')
}
$headlessArguments += @('-scriptPath', $PSScriptRoot, '-postScript', $ScriptName, $outputDirectory)
$headlessArguments += $FunctionAddress
$headlessArguments += @(
    '-log', (Join-Path $outputDirectory 'analysis.log'),
    '-scriptlog', (Join-Path $outputDirectory 'script.log')
)

& $javaPath @javaArguments @headlessArguments
if ($LASTEXITCODE -ne 0) { throw "Ghidra exited with code $LASTEXITCODE" }
$manifestPath = Join-Path $outputDirectory 'run.tsv'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw 'Ghidra did not produce a completed export manifest. Inspect the logs.'
}
$metadata = Import-Csv -LiteralPath $manifestPath -Delimiter "`t"
$recordedHash = ($metadata | Where-Object { $_.key -eq 'executable_sha256' }).value
if ($recordedHash -ne $expectedHash.ToLowerInvariant()) {
    throw 'Saved-project hash does not match the target. Do not use this evidence.'
}
Write-Output "Candidate evidence exported to $outputDirectory. Review logs and functions.tsv before drawing conclusions."
