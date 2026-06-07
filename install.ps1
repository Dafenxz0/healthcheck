[CmdletBinding()]
param(
    [string]$PackageUrl = "https://github.com/Dafenxz0/healthcheck/archive/refs/tags/v0.2.0.zip",
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "oss-repo-healthcheck"),
    [switch]$NoPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

function Find-Python {
    $candidates = @(
        @{ Command = "py"; Args = @("-3") },
        @{ Command = "python"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        $command = $candidate["Command"]
        $arguments = @($candidate["Args"]) + @("-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)")
        try {
            & $command @arguments *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        }
        catch {
            continue
        }
    }

    throw "Python 3.9 or newer was not found. Install Python from https://www.python.org/downloads/ and rerun this script."
}

if (-not $env:LOCALAPPDATA) {
    throw "LOCALAPPDATA is not set; pass -InstallDir to choose an install location."
}

$python = Find-Python
$venvDir = Join-Path $InstallDir ".venv"
$binDir = Join-Path $InstallDir "bin"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$shimPath = Join-Path $binDir "oss-repo-healthcheck.cmd"

New-Item -ItemType Directory -Force -Path $InstallDir, $binDir | Out-Null

Write-Host "Creating virtual environment in $venvDir"
Invoke-Checked -Command $python["Command"] -Arguments (@($python["Args"]) + @("-m", "venv", $venvDir))

Write-Host "Installing oss-repo-healthcheck from $PackageUrl"
Invoke-Checked -Command $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked -Command $venvPython -Arguments @("-m", "pip", "install", "--upgrade", $PackageUrl)

$shim = @"
@echo off
"$venvPython" -m oss_repo_healthcheck %*
"@
$shim | Set-Content -Path $shimPath -Encoding ASCII

if (-not $NoPath) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $entries = @()
    if ($userPath) {
        $entries = $userPath -split ";"
    }

    $alreadyPresent = $false
    foreach ($entry in $entries) {
        if ($entry.TrimEnd("\") -ieq $binDir.TrimEnd("\")) {
            $alreadyPresent = $true
            break
        }
    }

    if (-not $alreadyPresent) {
        $newPath = if ($userPath) { "$userPath;$binDir" } else { $binDir }
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        $env:Path = "$env:Path;$binDir"
        Write-Host "Added $binDir to the user PATH. Open a new terminal to use it everywhere."
    }
}

Write-Host ""
Write-Host "Installed oss-repo-healthcheck."
Write-Host "Run: $shimPath --help"
