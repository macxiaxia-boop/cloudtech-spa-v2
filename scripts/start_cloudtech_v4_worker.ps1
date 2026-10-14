<#
.SYNOPSIS
    Start the EXISTING CloudTech V4 local deterministic worker on Windows.
.DESCRIPTION
    Never creates a new repository, changes the network, edits the registry,
    installs a service, triggers paid models, or deploys to production.
    Use -Mode Loop only after manually choosing a supervised development DB.
.EXAMPLE
    $env:CLOUDTECH_ENV = 'development'
    .\scripts\start_cloudtech_v4_worker.ps1 -Mode Once -DbPath 'D:\CloudTech-Portable\data\v4_staging_runs.sqlite3'
#>
[CmdletBinding()]
param(
    [ValidateSet('Once','Loop')]
    [string]$Mode = 'Once',

    [string]$DbPath = $env:CLOUDTECH_V4_SQLITE_RUN_STORE
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$modeEnv = [string]$env:CLOUDTECH_ENV
if ($modeEnv.ToLowerInvariant() -notin @('test','development','staging')) {
    throw 'V4 local SQLite worker is restricted to an explicit test/development/staging environment.'
}
if ([string]::IsNullOrWhiteSpace($DbPath)) {
    throw 'Specify -DbPath or CLOUDTECH_V4_SQLITE_RUN_STORE. Never use a production DB.'
}
$fullDb = [System.IO.Path]::GetFullPath($DbPath)
$parent = Split-Path -Parent $fullDb
if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
    throw "Run DB parent directory does not exist: $parent"
}
if ($fullDb.StartsWith($repoRoot + [System.IO.Path]::DirectorySeparatorChar,
                       [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Run database must not live inside the publicly tracked CloudTech source tree.'
}
$py = Get-Command python -ErrorAction Stop
$repoModule = Join-Path $repoRoot 'workflows\v4\local_worker.py'
if (-not (Test-Path -LiteralPath $repoModule -PathType Leaf)) {
    throw "Expected V4 worker source missing: $repoModule"
}
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$repoRoot;$env:PYTHONPATH" } else { $repoRoot }
$env:CLOUDTECH_V4_SQLITE_RUN_STORE = $fullDb
Set-Location $repoRoot

Write-Host ("CloudTech V4 worker mode={0}, environment={1}" -f $Mode, $modeEnv)
Write-Host ("Store file: {0}" -f $fullDb)
Write-Host 'Allowed workpath: WP-LOCAL-ARTICLE-EXTRACT only. External provider calls: none.'
if ($Mode -eq 'Loop') {
    # Runs in this terminal. Ctrl+C stops it; not an unattended service install.
    & $py.Source -m workflows.v4.local_worker --db $fullDb --loop
} else {
    & $py.Source -m workflows.v4.local_worker --db $fullDb --once
}
exit $LASTEXITCODE
