<p align="center">
	<img src="src/splitshot/browser/static/githublogo.png" alt="SplitShot logo" width="240" />
</p>

# SplitShot

![Platforms](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-0f766e)
![Python](https://img.shields.io/badge/python-3.12-3776AB)
![Workflow](https://img.shields.io/badge/workflow-local--first-166534)
![UI](https://img.shields.io/badge/UI-browser--first-1d4ed8)
![License](https://img.shields.io/badge/license-MIT-111827)

Local-first competition shooting video analysis, scoring, merge review, and FFmpeg export.

SplitShot runs as a local browser application. The browser shell is the product surface for ingest, timing review, PractiScore comparison, overlay tuning, metrics review, and export.

## Highlights

- Browser-first workflow with local-only processing and no cloud dependency.
- Metrics dashboard built from derived timing and scoring state, with CSV and text export.
- Shared overlay model for imported PractiScore summaries plus repeatable custom text boxes.
- Real-time export log modal backed by the existing activity stream and FFmpeg pipeline callbacks.
- Cross-platform browser workflow for macOS, Windows, and Linux using the same project model, controller, and export code.

## Product Views

### Browser shell

![SplitShot browser shell](docs/assets/browser-shell.png)

## Support Matrix

| Surface | Supported OS | Validation browsers | Purpose |
| --- | --- | --- | --- |
| Browser shell | macOS, Windows, Linux | Chromium-class, Firefox, Safari-class WebKit | Primary workflow for media import, timing review, scoring, metrics, overlays, merge, and export |

## Getting Started

### Setup scripts

Use the repository scripts when you want a workstation-ready setup for local launch, tests, and browser validation.

- macOS and Linux: `scripts/setup_splitshot.sh`
- Windows PowerShell: `scripts/setup_splitshot.ps1`

Examples:

```bash
bash scripts/setup_splitshot.sh
uv run splitshot
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_splitshot.ps1
uv run splitshot
```

### Manual path

If you prefer to install tools yourself, SplitShot needs:

- `uv`
- Python 3.12
- `ffmpeg` and `ffprobe`
- a local desktop browser for validation

Then run:

```bash
uv sync --extra dev
uv run splitshot
```

## Launch Commands

```bash
uv run splitshot
uv run splitshot --no-open
uv run splitshot --check
uv run splitshot-web
```

`uv run splitshot` is the normal entrypoint. The default browser path is quiet in the terminal unless you request log mirroring with `--log-level` or explicitly choose `--no-open`.

## Validation Workflow

Use the commands below to validate the local runtime and browser shell.

```bash
uv run splitshot --check
uv run pytest
uv run python -m playwright install chromium firefox webkit
uv run python scripts/run_browser_ui_surface_audit.py
uv run python scripts/run_browser_av_audit.py
uv run python scripts/run_browser_interaction_audit.py --primary-video /path/to/Stage1.MP4 --merge-video /path/to/Stage2.MP4 --practiscore /path/to/IDPA.csv
```

The browser shell should be validated in real desktop browsers. Chromium, Firefox, and Safari-class WebKit checks are expected; the VS Code integrated browser is useful for debugging, but it is not a Safari substitute. Use the interaction audit when you need route-backed drag, scroll, PractiScore, and PiP coverage with actual media files.

## Export Pipeline

SplitShot exports locally with FFmpeg. The app renders the selected stage view, overlays, scoring badges, and merge layout into frames, then encodes the final output on the same machine.

Export controls cover:

- built-in presets plus custom settings
- aspect ratio and crop center
- output width and output height
- H.264 or HEVC video encoding
- bitrate, FFmpeg preset, and optional two-pass encoding
- AAC audio sample rate and bitrate
- real-time export logs stored on `project.export.last_log` and surfaced in the browser log modal

## Documentation

- Project documentation hub: [docs/README.md](docs/README.md)
- Architecture and data flow: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Development workflow: [docs/DEVELOPING.md](docs/DEVELOPING.md)
- Known constraints: [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
- End-user guide: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- Markdown inventory: [docs/MARKDOWN_INDEX.md](docs/MARKDOWN_INDEX.md)
- Package-level technical docs live beside the source in `src/splitshot/.../README.md`.

## Runtime Model

SplitShot is a source-first `uv` project. The expected workflow is a real desktop session with local media files, a visible browser, and platform-native file dialogs. Native `.dmg` or `.exe` packaging is intentionally out of scope for this repository.

`ffmpeg` and `ffprobe` are resolved from `PATH`, `SPLITSHOT_FFMPEG_DIR`, or vendored binaries under `src/splitshot/resources/ffmpeg/<platform>`.

## License

SplitShot is licensed under the MIT License. See [LICENSE](LICENSE).

**Last updated:** 2026-04-17
**Referenced files last updated:** 2026-04-17
