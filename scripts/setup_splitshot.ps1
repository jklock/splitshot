Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RootDir = Split-Path -Parent $PSScriptRoot
$PythonVersion = if ($env:SPLITSHOT_PYTHON_VERSION) { $env:SPLITSHOT_PYTHON_VERSION } else { '3.12' }

function Write-Setup([string]$Message) {
    Write-Host "[splitshot-setup] $Message"
}

function Get-CommandPath([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        return $null
    }
    return $command.Source
}

function Require-Winget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'winget is required on Windows. Install App Installer from Microsoft Store and re-run this script.'
    }
}

function Install-WingetPackage([string]$Id) {
    Write-Setup "Ensuring $Id is installed"
    winget install --id $Id --exact --accept-source-agreements --accept-package-agreements --silent | Out-Null
}

function Ensure-Uv {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        return
    }
    Require-Winget
    Install-WingetPackage 'astral-sh.uv'
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw 'uv was installed but is not available in this shell. Open a new PowerShell session and re-run the script.'
    }
}

function Ensure-WindowsDependencies {
    Require-Winget
    Install-WingetPackage 'Git.Git'
    Ensure-Uv
    Install-WingetPackage 'Gyan.FFmpeg'
    Install-WingetPackage 'Google.Chrome'
    Install-WingetPackage 'Mozilla.Firefox'
}

function Bootstrap-Workspace {
    Set-Location $RootDir
    Write-Setup "Installing Python $PythonVersion through uv"
    uv python install $PythonVersion
    Write-Setup 'Syncing project dependencies'
    uv sync --extra dev
    Write-Setup 'Installing Playwright browser runtimes for validation'
    uv run python -m playwright install chromium firefox webkit
    Write-Setup 'Running SplitShot runtime check'
    uv run splitshot --check
}

Ensure-WindowsDependencies
Bootstrap-Workspace

Write-Host ''
Write-Host '[splitshot-setup] Ready.'
Write-Host '[splitshot-setup] Launch commands:'
Write-Host '  uv run splitshot'
Write-Host '  uv run splitshot --desktop'
Write-Host '  uv run pytest'