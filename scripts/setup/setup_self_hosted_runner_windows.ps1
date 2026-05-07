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

function Resolve-RunnerDir {
    param([string]$ExplicitRunnerDir)

    $candidates = @()
    if ($ExplicitRunnerDir) {
        $candidates += $ExplicitRunnerDir
    }
    if ($env:SPLITSHOT_RUNNER_DIR) {
        $candidates += $env:SPLITSHOT_RUNNER_DIR
    }
    $candidates += @(
        'C:\actions-runner\splitshot-win',
        'C:\actions-runner',
        'D:\actions-runner\splitshot-win',
        'D:\actions-runner',
        (Join-Path $env:USERPROFILE 'actions-runner\splitshot-win'),
        (Join-Path $env:USERPROFILE 'actions-runner')
    )

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

    throw 'Could not locate the existing GitHub Actions runner directory. Set -RunnerDir or SPLITSHOT_RUNNER_DIR.'
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
Write-Setup "Using runner directory $resolvedRunnerDir"
Ensure-RunnerService $resolvedRunnerDir

Write-Setup "bash: $(bash --version | Select-Object -First 1)"
Write-Setup "git: $(git --version)"
Write-Setup "python: $((& $pythonExe --version | Select-Object -First 1))"
Write-Setup "uv: $(uv --version)"
Write-Setup "ffmpeg: $((ffmpeg -version | Select-Object -First 1))"
