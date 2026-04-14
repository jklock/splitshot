<p align="center">
	<img src="src/splitshot/browser/static/logo.png" alt="SplitShot logo" width="240" />
</p>

# SplitShot

Local-first competition shooting video analysis, merge, scoring, and export.

## Documentation

- Project documentation hub: [docs/README.md](docs/README.md)
- Architecture and data flow: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Development workflow: [docs/DEVELOPING.md](docs/DEVELOPING.md)
- Known constraints: [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
- End-user guide: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- Markdown inventory: [docs/MARKDOWN_INDEX.md](docs/MARKDOWN_INDEX.md)
- Package-level technical docs live beside the source in `src/splitshot/.../README.md`.

## Setup

SplitShot uses `uv` to provision its pinned Python 3.12 environment. From a cloned repository, `uv run splitshot` is the normal launch command and `uv` will create or reuse the environment automatically. You still need `uv` plus FFmpeg and FFprobe on your `PATH`, or vendored under `src/splitshot/resources/ffmpeg/<platform>`.

### macOS

1. Install Homebrew if you do not already have it.
2. Install the required tools:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install git uv ffmpeg
```

3. Verify that the tools resolve from a fresh terminal:

```bash
uv --version
ffmpeg -version
ffprobe -version
```

4. Clone the repository and enter it:

```bash
git clone https://github.com/jklock/splitshot.git
cd splitshot
```

5. Start the browser UI from the repository root:

```bash
uv run splitshot
```

6. Optional commands:

```bash
uv run splitshot --desktop
uv run splitshot --no-open
uv run splitshot --check
```

7. Development-only extras for tests and browser audits:

```bash
uv sync --extra dev
```

### Windows

1. Install Git if it is not already present.
2. Install `uv`:

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

3. Download a Windows FFmpeg build that includes both `ffmpeg.exe` and `ffprobe.exe`, extract it to a stable folder such as `C:\Tools\ffmpeg`, and keep the `bin` folder handy.
4. Add FFmpeg to `PATH`:
   - Open Start and search for `Environment Variables`.
   - Open `Edit the system environment variables`.
   - Click `Environment Variables`.
   - Under either User variables or System variables, select `Path` and click `Edit`.
   - Click `New` and add the folder that contains `ffmpeg.exe` and `ffprobe.exe`, for example `C:\Tools\ffmpeg\bin`.
   - Click `OK` through every dialog, then open a new PowerShell or Windows Terminal window so the updated `PATH` loads.
5. Verify the installation from a fresh terminal:

```powershell
uv --version
ffmpeg -version
ffprobe -version
```

6. Clone the repository:

```powershell
git clone https://github.com/jklock/splitshot.git
Set-Location splitshot
```

7. Run SplitShot:

```powershell
uv run splitshot
uv run splitshot --desktop
uv run splitshot --no-open
uv run splitshot --check
```

If you would rather not edit `PATH`, set `SPLITSHOT_FFMPEG_DIR` to the folder that contains `ffmpeg.exe` and `ffprobe.exe` before launching SplitShot.

8. Development-only extras for tests and browser audits:

```powershell
uv sync --extra dev
```

### Linux

1. Install Git, `uv`, FFmpeg, and FFprobe. Example for Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install -y git curl ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Verify the tools from a fresh terminal:

```bash
uv --version
ffmpeg -version
ffprobe -version
```

3. Clone the repository and run SplitShot:

```bash
git clone https://github.com/jklock/splitshot.git
cd splitshot
uv run splitshot
```

4. Optional commands:

```bash
uv run splitshot --desktop
uv run splitshot --no-open
uv run splitshot --check
```

5. Development-only extras for tests and browser audits:

```bash
uv sync --extra dev
```

## Run

Once setup is complete, the day-to-day commands are below. The browser UI opens locally at `127.0.0.1:8765`, and `--desktop` starts the PySide6 window.

```bash
uv run splitshot
uv run splitshot --desktop
uv run splitshot --no-open
uv run splitshot --check
```

Compatibility aliases are also available:

```bash
uv run splitshot-web
uv run splitshot-desktop
```

## Validation

Use these commands to confirm the install and the local toolchain.

```bash
uv sync --extra dev
uv run pytest
uv run splitshot --check
uv run python -m playwright install chromium firefox webkit
uv run python scripts/run_browser_ui_surface_audit.py
```

The Playwright audit defaults to the available Chromium, Firefox, and Safari-class WebKit targets, and it also uses the locally installed Chrome or Edge channels when they are present. The VS Code integrated browser is effectively a Chromium debugging surface, so use the Playwright script from the VS Code terminal for actual cross-browser validation.

## Export

SplitShot exports with local FFmpeg. The app renders the selected video/merge, overlays, and scoring into frames, then encodes a local video file with the selected export variables.

Browser export controls expose:

- Presets: Source MP4, Universal Vertical Master, Short-Form Vertical, YouTube Long-Form 1080p, YouTube Long-Form 4K, and Custom.
- Video: aspect ratio, crop center, target width/height, source/30/60 fps, H.264 or HEVC, bitrate, FFmpeg preset, and optional two-pass encode.
- Audio: AAC, sample rate, and bitrate.
- Color: Rec.709 SDR.
- Containers: output path extensions `.mp4`, `.m4v`, `.mov`, and `.mkv` are supported.
- Logs: the Export pane stores the FFmpeg command/log output for the last export so failures are visible.

Browser file pickers and typed-path imports support common stage containers including `.mp4`, `.m4v`, `.mov`, `.avi`, `.wmv`, `.webm`, `.mkv`, `.mpg`, `.mpeg`, `.mts`, and `.m2ts`.

## Runtime Model

SplitShot is a source-first, uv-only project. The expected launch path is `uv run splitshot` from a clone or installed source checkout, and native `.dmg` / `.exe` packaging is intentionally out of scope for the current workflow.

The app still needs `ffmpeg` and `ffprobe`. It resolves them from `PATH`, `SPLITSHOT_FFMPEG_DIR`, or vendored binaries under `src/splitshot/resources/ffmpeg/<platform>`.

## License

SplitShot is licensed under the MIT License. See [LICENSE](LICENSE).

**Last updated:** 2026-04-14
**Referenced files last updated:** 2026-04-14
