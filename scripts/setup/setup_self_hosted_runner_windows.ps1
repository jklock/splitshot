param(
    [string]$RunnerDir = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSNativeCommandUseErrorActionPreference = $false
}

function Write-Setup([string]$Message) {
    Write-Host "[splitshot-runner-setup] $Message"
}

function Test-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Add-PathIfPresent([string]$PathEntry) {
    if (-not (Test-Path $PathEntry)) {
        return
    }
    $pathParts = @($env:Path -split ';' | Where-Object { $_ })
    if ($pathParts -contains $PathEntry) {
        return
    }
    $env:Path = "$PathEntry;$env:Path"
}

function Require-Env([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Missing required environment variable: $Name"
    }
    return $value
}

function Ensure-Chocolatey {
    if (Test-Command choco) {
        return
    }
    Write-Setup 'Installing Chocolatey'
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Add-PathIfPresent 'C:\ProgramData\chocolatey\bin'
    if (-not (Test-Command choco)) {
        throw 'Chocolatey installation completed but choco is still unavailable in this shell.'
    }
}

function Test-ChocoPackageInstalled([string]$Name) {
    if (-not (Test-Command choco)) {
        return $false
    }
    $output = & choco list --local-only --exact --limit-output $Name 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    return ($output | Where-Object { $_ -match "^$([Regex]::Escape($Name))\|" } | Measure-Object).Count -gt 0
}

function Ensure-ChocoPackage([string]$Name) {
    Ensure-Chocolatey
    if (Test-ChocoPackageInstalled $Name) {
        Write-Setup "$Name already installed"
        return
    }
    Write-Setup "Installing $Name"
    & choco install -y $Name --no-progress
}

function Ensure-GitBash {
    if (Test-Command bash) {
        return
    }
    Ensure-ChocoPackage 'git'
    Add-PathIfPresent 'C:\Program Files\Git\bin'
    Add-PathIfPresent 'C:\Program Files\Git\usr\bin'
    if (-not (Test-Command bash)) {
        throw 'Git was installed but bash is still unavailable in this shell.'
    }
}

function Ensure-FFmpeg {
    if (Test-Command ffmpeg) {
        return
    }
    Ensure-ChocoPackage 'ffmpeg'
    if (-not (Test-Command ffmpeg)) {
        throw 'ffmpeg was installed but is still unavailable in this shell.'
    }
}

function Add-Python312Paths {
    $candidates = @(
        'C:\Python312',
        'C:\Python312\Scripts',
        'C:\tools\python312',
        'C:\tools\python312\Scripts',
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\Scripts')
    )
    foreach ($candidate in $candidates) {
        Add-PathIfPresent $candidate
    }
}

function Get-Python312Exe {
    if (Test-Command py) {
        try {
            $exe = (& py -3.12 -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1).Trim()
            if ($LASTEXITCODE -eq 0 -and $exe -and (Test-Path $exe)) {
                return $exe
            }
        } catch {
        }
    }

    $candidates = @(
        'C:\Python312\python.exe',
        'C:\tools\python312\python.exe',
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe')
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    if (Test-Command python) {
        try {
            $version = (& python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null | Select-Object -First 1).Trim()
            if ($LASTEXITCODE -eq 0 -and $version -eq '3.12') {
                return (Get-Command python).Source
            }
        } catch {
        }
    }

    return $null
}

function Ensure-Python312 {
    Add-Python312Paths
    $pythonExe = Get-Python312Exe
    if ($pythonExe) {
        return $pythonExe
    }
    Ensure-ChocoPackage 'python312'
    Add-Python312Paths
    $pythonExe = Get-Python312Exe
    if ($pythonExe) {
        return $pythonExe
    }
    throw 'Python 3.12 was installed but no usable Python 3.12 executable could be found.'
}

function Ensure-Uv {
    if (Test-Command uv) {
        return (Ensure-Python312)
    }
    $pythonExe = Ensure-Python312
    Write-Setup 'Installing uv with pip'
    & $pythonExe -m pip install --upgrade pip uv
    $scriptsDir = & $pythonExe -c "import site; print(site.USER_BASE + r'\Scripts')"
    Add-PathIfPresent $scriptsDir
    if (-not (Test-Command uv)) {
        throw 'uv was installed but is still unavailable in this shell.'
    }
    return $pythonExe
}

function RunnerDirCandidates([string]$ExplicitRunnerDir) {
    $candidates = @()
    if ($ExplicitRunnerDir) { $candidates += $ExplicitRunnerDir }
    if ($env:SPLITSHOT_RUNNER_DIR) { $candidates += $env:SPLITSHOT_RUNNER_DIR }
    $candidates += @(
        'C:\actions-runner\splitshot-win',
        'D:\actions-runner\splitshot-win',
        (Join-Path $env:USERPROFILE 'actions-runner\splitshot-win'),
        'C:\actions-runner',
        'D:\actions-runner',
        (Join-Path $env:USERPROFILE 'actions-runner')
    )
    return $candidates
}

function Find-ExistingRunnerDir([string]$ExplicitRunnerDir) {
    $candidates = RunnerDirCandidates $ExplicitRunnerDir

    foreach ($candidate in $candidates) {
        if (-not $candidate) {
            continue
        }
        if (-not (Test-Path $candidate)) {
            continue
        }
        if (Test-Path (Join-Path $candidate '.service')) {
            return (Resolve-Path $candidate).Path
        }
        $serviceFile = Get-ChildItem -Path $candidate -Filter '.service' -File -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($serviceFile) {
            return $serviceFile.Directory.FullName
        }
    }

    return $null
}

function Resolve-RunnerDir {
    param([string]$ExplicitRunnerDir)

    $existing = Find-ExistingRunnerDir $ExplicitRunnerDir
    if ($existing) {
        return $existing
    }
    $desired = $ExplicitRunnerDir
    if (-not $desired) {
        $desired = if ($env:SPLITSHOT_RUNNER_DIR) { $env:SPLITSHOT_RUNNER_DIR } else { 'C:\actions-runner\splitshot-win' }
    }
    return $desired
}

function Get-LatestRunnerAssetUrl {
    Ensure-Chocolatey
    $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/actions/runner/releases/latest' -Headers @{ 'User-Agent' = 'splitshot-runner-setup' }
    $asset = $release.assets | Where-Object { $_.name -match '^actions-runner-win-x64-.*\.zip$' } | Select-Object -First 1
    if (-not $asset) {
        throw 'Could not find a Windows x64 runner asset in the latest actions/runner release.'
    }
    return $asset.browser_download_url
}

function Ensure-RunnerFiles([string]$ResolvedRunnerDir) {
    if ((Test-Path (Join-Path $ResolvedRunnerDir 'config.cmd')) -and (Test-Path (Join-Path $ResolvedRunnerDir 'run.cmd'))) {
        Write-Setup "Runner files already present in $ResolvedRunnerDir"
        return
    }

    Write-Setup "Installing GitHub Actions runner into $ResolvedRunnerDir"
    New-Item -ItemType Directory -Path $ResolvedRunnerDir -Force | Out-Null
    $zipPath = Join-Path ([IO.Path]::GetTempPath()) 'actions-runner-win-x64.zip'
    $extractDir = Join-Path ([IO.Path]::GetTempPath()) ("actions-runner-extract-" + [guid]::NewGuid().ToString("N"))
    $assetUrl = Get-LatestRunnerAssetUrl
    Invoke-WebRequest -Uri $assetUrl -OutFile $zipPath
    New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force
    Copy-Item -Path (Join-Path $extractDir '*') -Destination $ResolvedRunnerDir -Recurse -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
}

function Ensure-RunnerConfigured([string]$ResolvedRunnerDir) {
    if (Test-Path (Join-Path $ResolvedRunnerDir '.runner')) {
        Write-Setup 'Runner already configured'
        return
    }

    $url = Require-Env 'GITHUB_RUNNER_URL'
    $token = Require-Env 'GITHUB_RUNNER_TOKEN'
    $runnerName = if ($env:GITHUB_RUNNER_NAME) { $env:GITHUB_RUNNER_NAME } else { $env:COMPUTERNAME }
    $runnerWorkDir = if ($env:GITHUB_RUNNER_WORKDIR) { $env:GITHUB_RUNNER_WORKDIR } else { '_work' }
    $labels = if ($env:GITHUB_RUNNER_LABELS) { $env:GITHUB_RUNNER_LABELS } else { '' }

    Write-Setup "Configuring runner $runnerName"
    $arguments = @(
        '--unattended',
        '--replace',
        '--runasservice',
        '--url', $url,
        '--token', $token,
        '--name', $runnerName,
        '--work', $runnerWorkDir
    )
    if ($labels) {
        $arguments += @('--labels', $labels)
    }
    Push-Location $ResolvedRunnerDir
    try {
        & .\config.cmd @arguments
    } finally {
        Pop-Location
    }
}

function Ensure-RunnerService([string]$ResolvedRunnerDir) {
    $serviceMarker = Join-Path $ResolvedRunnerDir '.service'
    if (-not (Test-Path $serviceMarker)) {
        throw "Runner directory $ResolvedRunnerDir does not contain a .service file."
    }

    $serviceName = (Get-Content $serviceMarker -ErrorAction Stop | Select-Object -First 1).Trim()
    if (-not $serviceName) {
        throw "Runner service marker $serviceMarker is empty."
    }

    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if (-not $service) {
        $service = Get-Service 'actions.runner.*' -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    if (-not $service) {
        throw "Could not find a Windows service for runner $serviceName."
    }

    if ($service.Status -ne 'Running') {
        Write-Setup "Starting runner service $($service.Name)"
        Start-Service -Name $service.Name
        $service.WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
    } else {
        Write-Setup "Runner service $($service.Name) already running"
    }

    Get-Service -Name $service.Name
}

Ensure-Chocolatey
Ensure-GitBash
Ensure-FFmpeg
$pythonExe = Ensure-Uv

$resolvedRunnerDir = Resolve-RunnerDir -ExplicitRunnerDir $RunnerDir
Ensure-RunnerFiles $resolvedRunnerDir
Ensure-RunnerConfigured $resolvedRunnerDir
Write-Setup "Using runner directory $resolvedRunnerDir"
Ensure-RunnerService $resolvedRunnerDir

Write-Setup "bash: $(bash --version | Select-Object -First 1)"
Write-Setup "git: $(git --version)"
Write-Setup "python: $((& $pythonExe --version | Select-Object -First 1))"
Write-Setup "uv: $(uv --version)"
Write-Setup "ffmpeg: $((ffmpeg -version | Select-Object -First 1))"
