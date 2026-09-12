#!/usr/bin/env pwsh
<#
.SYNOPSIS
  One-command installer for the standalone `providence` CLI binary (Windows).

.DESCRIPTION
  Installs `providence` only — it does not fetch or manage `sdd-compile`. `sdd`
  resolves `sdd-compile` on its own at runtime (env var, local build, PATH,
  wheel-bundled asset, or a verified version-tagged download), unchanged by
  this installer. See
  packages/core/providence_core/src/providence_core/utils/compiler_runner.py.

  Versioning: defaults to the latest GitHub release. Pass -Version <tag> to
  pin a specific release. Rollback is re-running this script with
  -Version <previous-tag> — there is no separate rollback command.

.PARAMETER Version
  Release tag to install (e.g. v1.2.3). Defaults to the latest release.

.PARAMETER InstallDir
  Install location. Defaults to $env:SDD_INSTALL_DIR, or
  "$env:LOCALAPPDATA\providence\bin" if unset.

.EXAMPLE
  irm https://raw.githubusercontent.com/SergioLacerda/providence/main/install.ps1 | iex
.EXAMPLE
  ./install.ps1 -Version v1.2.3
#>

param(
    [string]$Version = "",
    [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"

$Repo = "SergioLacerda/providence"
$Asset = "providence-windows-amd64.exe"
# Override point for CI smoke coverage (see install.sh's matching comment).
# Unset in normal use — real installs always hit the real GitHub release.
$BaseUrlOverride = $env:SDD_INSTALL_BASE_URL

if (-not $InstallDir) {
    if ($env:SDD_INSTALL_DIR) {
        $InstallDir = $env:SDD_INSTALL_DIR
    } else {
        $InstallDir = Join-Path $env:LOCALAPPDATA "sdd\bin"
    }
}

function Resolve-Tag {
    param([string]$RequestedVersion)
    if ($RequestedVersion) {
        return $RequestedVersion
    }
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest"
    if (-not $release.tag_name) {
        throw "Could not resolve the latest release tag from the GitHub API"
    }
    return $release.tag_name
}

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLower()
}

function Main {
    if ($BaseUrlOverride) {
        $tag = "local"
        $baseUrl = $BaseUrlOverride
    } else {
        $tag = Resolve-Tag -RequestedVersion $Version
        $baseUrl = "https://github.com/$Repo/releases/download/$tag"
    }

    Write-Host "Installing providence $tag ($Asset) to $InstallDir"

    $tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $tmpDir | Out-Null
    try {
        $assetPath = Join-Path $tmpDir $Asset
        $sumsPath = Join-Path $tmpDir "SHA256SUMS"

        Write-Host "Downloading $Asset..."
        Invoke-WebRequest -Uri "$baseUrl/$Asset" -OutFile $assetPath

        Write-Host "Downloading SHA256SUMS..."
        Invoke-WebRequest -Uri "$baseUrl/SHA256SUMS" -OutFile $sumsPath

        $sumsLine = Select-String -Path $sumsPath -Pattern " $Asset$" | Select-Object -First 1
        if (-not $sumsLine) {
            throw "SHA256SUMS for $tag has no entry for $Asset"
        }
        $expectedSum = ($sumsLine.Line -split '\s+')[0].ToLower()
        $actualSum = Get-Sha256 -Path $assetPath

        if ($expectedSum -ne $actualSum) {
            throw "Checksum mismatch for $Asset`n  expected: $expectedSum`n  actual:   $actualSum"
        }
        Write-Host "Checksum verified."

        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        $destPath = Join-Path $InstallDir "providence.exe"
        Copy-Item -Path $assetPath -Destination $destPath -Force

        Write-Host "Installed providence $tag to $destPath"

        $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if ($userPath -notlike "*$InstallDir*") {
            Write-Host "NOTE: $InstallDir is not on your PATH. Add it, e.g.:"
            Write-Host "  [Environment]::SetEnvironmentVariable('Path', `"`$env:Path;$InstallDir`", 'User')"
        }

        & $destPath version
    }
    finally {
        Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
    }
}

Main
