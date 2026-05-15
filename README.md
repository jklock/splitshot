<p align="center">
	<img src="src/splitshot/browser/static/githublogo.png" alt="SplitShot logo" width="800" />
</p>

# SplitShot

SplitShot is a local-first browser app for competition shooting video analysis, split timing, scoring, review overlays, PiP comparison, metrics, and final video export.

<img src="docs/screenshots/ProjectPane.png" alt="SplitShot browser app showing the Project pane and video review workspace" width="1000">

## Start Here

If you just forked SplitShot, read these in order:

1. This `README.md` for install, quickstart, and repo shape.
2. [docs/project/DEVELOPING.md](docs/project/DEVELOPING.md) for the day-1 developer workflow.
3. [docs/project/ARCHITECTURE.md](docs/project/ARCHITECTURE.md) for runtime layers, ownership, and data flow.
4. [docs/tests/TEST_SUITE_GUIDE.md](docs/tests/TEST_SUITE_GUIDE.md) for the validation strategy and suite map.
5. [scripts/README.md](scripts/README.md) for operational scripts, audits, release helpers, and analysis tooling.

If you only need the product docs, start with [docs/userfacing/USER_GUIDE.md](docs/userfacing/USER_GUIDE.md).

## What SplitShot Does

- Imports local stage video and keeps the workflow on your machine.
- Detects the start beep and shot events from audio with the built-in ShotML pipeline.
- Lets you review, fix, and extend timing data in the waveform and split editor.
- Supports manual scoring or PractiScore-backed stage context.
- Composes live overlays, review boxes, and marker callouts on the preview and final export.
- Adds PiP, side-by-side, or above-below supporting media.
- Exports metrics, summaries, and a finished local video render through FFmpeg.

## Install

SplitShot runs from source or as a macOS Electron app.

### Prerequisites

- `uv`: [docs.astral.sh/uv/getting-started/installation](https://docs.astral.sh/uv/getting-started/installation/)
- `ffmpeg`: [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
- `git`: [git-scm.com/downloads](https://git-scm.com/downloads)

### Source Install

```bash
git clone https://github.com/jklock/splitshot.git
cd splitshot
uv python install 3.12
uv sync --extra dev
uv run splitshot
```

If the browser does not open automatically, retry with `uv run splitshot --no-open` and open the printed URL manually.

### Runtime Check

```bash
uv run splitshot --check
```

### Electron App

The Electron shell targets macOS packaging and release signing. Use [docs/project/ELECTRON_RELEASE.md](docs/project/ELECTRON_RELEASE.md) for the packaging and notarization workflow.

## Quickstart

1. Launch `uv run splitshot`.
2. Create or select a project in the `Project` pane.
3. Import the primary video and let analysis detect the start beep and shots.
4. Review timing in `ShotML` and `Splits`.
5. Score the run, configure overlay/review output, and add PiP media if needed.
6. Review metrics, then export the final video.

For the user workflow, continue with [docs/userfacing/workflow.md](docs/userfacing/workflow.md).

## Repo Reading Path

### For fork owners and maintainers

- [docs/README.md](docs/README.md): full documentation index by audience
- [docs/project/DEVELOPING.md](docs/project/DEVELOPING.md): local setup, first commands, and daily workflow
- [docs/project/ARCHITECTURE.md](docs/project/ARCHITECTURE.md): controller, project model, browser shell, analysis, export
- [src/splitshot/README.md](src/splitshot/README.md): source tree map and code entrypoints
- [docs/tests/TEST_SUITE_GUIDE.md](docs/tests/TEST_SUITE_GUIDE.md): which tests own which contracts
- [scripts/README.md](scripts/README.md): script inventory and when to use each tool
- [docs/project/LIMITATIONS.md](docs/project/LIMITATIONS.md): current intentional constraints and known boundaries

### For users

- [docs/userfacing/USER_GUIDE.md](docs/userfacing/USER_GUIDE.md)
- [docs/userfacing/workflow.md](docs/userfacing/workflow.md)
- [docs/userfacing/troubleshooting.md](docs/userfacing/troubleshooting.md)
- [docs/userfacing/panes/](docs/userfacing/panes/)

## Common Commands

```bash
uv sync --extra dev
uv run splitshot
uv run splitshot --headless
uv run splitshot --check
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
uvx ruff check .
uvx ruff format .
```

## Read This Next

- [docs/README.md](docs/README.md) for the full documentation index
- [CONTRIBUTING.md](CONTRIBUTING.md) for change workflow and review expectations
- [docs/tests/TEST_SUITE_GUIDE.md](docs/tests/TEST_SUITE_GUIDE.md) for validation
- [scripts/README.md](scripts/README.md) for maintenance scripts
- [docs/project/ELECTRON_RELEASE.md](docs/project/ELECTRON_RELEASE.md) for packaged-app release work

## License

SplitShot is licensed under the MIT License. See [LICENSE](LICENSE).
