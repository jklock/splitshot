<p align="center">
	<img src="src/splitshot/browser/static/githublogo.png" alt="SplitShot logo" width="640" />
</p>

# SplitShot

SplitShot is a local-first browser app for competition shooting video analysis, split timing, scoring, PiP review, overlay tuning, metrics, and final video export.

<img src="docs/screenshots/ProjectPane.png" alt="SplitShot browser app showing the Project pane and video review workspace" width="1000">

## What SplitShot Does

- Import a local stage video without uploading it to the cloud.
- Detect the timer beep and shot events from the video's audio.
- Review and correct split timing in the waveform editor.
- Score the run manually or load PractiScore context for the same stage.
- Tune on-video shot badges, timer badges, score summaries, and review text boxes.
- Add PiP media such as a second angle or still images.
- Review derived metrics, then export CSV or text summaries.
- Render a finished local video with FFmpeg.

## Install SplitShot

SplitShot runs directly from this repository. The shortest path is:

1. Download this repo to a local folder.
2. Run the setup script for your platform.
3. Launch `uv run splitshot`.
4. Import a video and start editing.

### What To Download

- SplitShot source code: [GitHub repo](https://github.com/jklock/splitshot)
- Direct ZIP download if you do not want to use Git: [main branch ZIP](https://github.com/jklock/splitshot/archive/refs/heads/main.zip)
- Homebrew for macOS setup: [brew.sh](https://brew.sh)
- `winget` / App Installer for Windows setup: [Windows Package Manager docs](https://learn.microsoft.com/windows/package-manager/winget/)
- `uv` docs if you want to install it yourself: [Astral uv installation](https://docs.astral.sh/uv/getting-started/installation/)
- FFmpeg download reference: [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
- Git download reference: [git-scm.com/downloads](https://git-scm.com/downloads)
- Browser downloads if you need them manually: [Google Chrome](https://www.google.com/chrome/) and [Firefox](https://www.mozilla.org/firefox/new/)

### 1. Download The Repo To A Local Folder

If you already have Git, clone the repo into a local work folder.

#### macOS or Linux

```bash
mkdir -p ~/Code
cd ~/Code
git clone https://github.com/jklock/splitshot.git
cd splitshot
```

#### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force C:\Code | Out-Null
Set-Location C:\Code
git clone https://github.com/jklock/splitshot.git
Set-Location .\splitshot
```

If you do not have Git yet, download the ZIP instead.

1. Open [the SplitShot repo page](https://github.com/jklock/splitshot) or the [direct ZIP link](https://github.com/jklock/splitshot/archive/refs/heads/main.zip).
2. Download the ZIP.
3. Unzip it into `~/Code` on macOS/Linux or `C:\Code` on Windows.
4. If GitHub names the extracted folder `splitshot-main`, either rename it to `splitshot` or use that folder name in the commands below.

### 2. Run The Platform Setup Script

The setup scripts install Python 3.12 through `uv`, sync the project dependencies, install Playwright browser runtimes used by the repo, and run `uv run splitshot --check` at the end.

#### macOS

Install Homebrew first if it is not already installed.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then open Terminal, move into the SplitShot folder, and run:

```bash
cd ~/Code/splitshot
bash scripts/setup/setup_splitshot.sh
```

What the macOS setup script installs for you:

- `git`
- `uv`
- `ffmpeg` and `ffprobe`
- Google Chrome
- Firefox
- Python 3.12
- SplitShot dependencies and test browser runtimes

#### Linux

The Linux setup script supports `apt-get`, `dnf`, `pacman`, and `zypper`. If your distro uses something else, skip to the manual setup section.

```bash
cd ~/Code/splitshot
bash scripts/setup/setup_splitshot.sh
```

What the Linux setup script installs for you:

- `git`
- `curl`
- `ffmpeg` and `ffprobe`
- Firefox
- Chromium when the package exists for your distro
- `uv`
- Python 3.12
- SplitShot dependencies and test browser runtimes

#### Windows PowerShell

Install App Installer / `winget` first if it is not already available on your machine.

Then open PowerShell, move into the SplitShot folder, and run:

```powershell
Set-Location C:\Code\splitshot
powershell -ExecutionPolicy Bypass -File .\scripts\setup\setup_splitshot.ps1
```

What the Windows setup script installs for you:

- Git
- `uv`
- FFmpeg and FFprobe
- Google Chrome
- Firefox
- Python 3.12
- SplitShot dependencies and test browser runtimes

### 3. Launch SplitShot

After setup completes, launch the app from the repo root:

```bash
uv run splitshot
```

Useful launch commands:

```bash
uv run splitshot
uv run splitshot --no-open
uv run splitshot --check
```

- Use `uv run splitshot` for normal use.
- Use `uv run splitshot --no-open` if you want the local server without automatically opening a browser window.
- Use `uv run splitshot --check` if you want to validate the local toolchain again.

If the browser does not open automatically, use the local URL printed in the terminal and open it in Chrome or Firefox.

### Manual Setup

Use this path if you do not want the bootstrap script or if your machine cannot use the script's package-manager assumptions.

#### macOS manual setup

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install git uv ffmpeg
brew install --cask google-chrome firefox
cd ~/Code/splitshot
uv python install 3.12
uv sync --extra dev
uv run python -m playwright install chromium firefox webkit
uv run splitshot --check
uv run splitshot
```

#### Linux manual setup

Install Git, curl, FFmpeg, and a desktop browser with your distro package manager, then run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
cd ~/Code/splitshot
uv python install 3.12
uv sync --extra dev
uv run python -m playwright install chromium firefox webkit
uv run splitshot --check
uv run splitshot
```

Examples for common package managers:

```bash
sudo apt-get update && sudo apt-get install -y git curl ffmpeg firefox
sudo dnf install -y git curl ffmpeg ffmpeg-libs firefox chromium
sudo pacman -Sy --noconfirm git curl ffmpeg firefox chromium
sudo zypper install -y git curl ffmpeg MozillaFirefox chromium
```

#### Windows manual setup

If you have `winget`, you can install everything manually with:

```powershell
winget install --id Git.Git --exact --accept-source-agreements --accept-package-agreements
winget install --id astral-sh.uv --exact --accept-source-agreements --accept-package-agreements
winget install --id Gyan.FFmpeg --exact --accept-source-agreements --accept-package-agreements
winget install --id Google.Chrome --exact --accept-source-agreements --accept-package-agreements
winget install --id Mozilla.Firefox --exact --accept-source-agreements --accept-package-agreements
Set-Location C:\Code\splitshot
uv python install 3.12
uv sync --extra dev
uv run python -m playwright install chromium firefox webkit
uv run splitshot --check
uv run splitshot
```

If you do not have `winget`, install Git, `uv`, FFmpeg, Chrome, and Firefox from the download pages linked above, then run the same `uv` commands.

### First Run

Once SplitShot is open in your browser:

1. Create a new project or open an existing `.ssproj` bundle.
2. Select the primary stage video.
3. Wait for the local audio analysis to detect the beep and shots.
4. Adjust timing in Splits, then move on to Score, Overlay, Review, PiP, Metrics, and Export.

## Basic Workflow

1. Open SplitShot and create or reopen a project in the Project pane.
2. Select the primary video, or paste a direct local path and press Enter for very large files.
3. Wait for local analysis to detect the beep and shots.
4. Fix timing in Splits before you score or style anything.
5. Import PractiScore if you want official stage context.
6. Use Score, Overlay, and Review to set the scoring and on-video presentation.
7. Add PiP media if you want a second angle or supporting images.
8. Export the final video and keep the project bundle for later revisions.

## App Guides

- [Project](docs/userfacing/panes/project.md)
- [Splits](docs/userfacing/panes/splits.md)
- [Score](docs/userfacing/panes/score.md)
- [PiP](docs/userfacing/panes/pip.md)
- [Overlay](docs/userfacing/panes/overlay.md)
- [Review](docs/userfacing/panes/review.md)
- [Export](docs/userfacing/panes/export.md)
- [Metrics](docs/userfacing/panes/metrics.md)

## More Documentation

- [Full user guide](docs/userfacing/USER_GUIDE.md)
- [Workflow guide](docs/userfacing/workflow.md)
- [Troubleshooting](docs/userfacing/troubleshooting.md)
- [Documentation hub](docs/README.md)
- [Current limitations](docs/project/LIMITATIONS.md)

## License

SplitShot is licensed under the MIT License. See [LICENSE](LICENSE).

**Last updated:** 2026-04-18
**Referenced files last updated:** 2026-04-18
