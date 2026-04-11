$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

uv run pyinstaller --noconfirm packaging/splitshot.spec

$Exe = Join-Path $Root "dist\SplitShot\SplitShot.exe"
if (!(Test-Path $Exe)) {
    throw "Expected build output was not created: $Exe"
}

Write-Host "Built $Exe"
