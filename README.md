<p align="center">
	<img src="src/splitshot/browser/static/githublogo.png" alt="SplitShot logo" width="220" />
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

## Who It's For

- Shooters reviewing match footage and classifier runs.
- Editors building stage recap videos with timing and scoring overlays.
- Anyone who wants local processing instead of cloud upload workflows.

## Install Requirements

- Python 3.12
- `uv`
- `ffmpeg` and `ffprobe`
- A desktop browser

## Install And Launch

### macOS and Linux

```bash
bash scripts/setup/setup_splitshot.sh
uv run splitshot
```

### Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup\setup_splitshot.ps1
uv run splitshot
```

### Manual Setup

```bash
uv sync --extra dev
uv run splitshot
```

Useful launch commands:

```bash
uv run splitshot
uv run splitshot --no-open
uv run splitshot --check
```

Use `--no-open` when you want the local server without launching a browser window. Use `--check` when you want to validate the local toolchain before a session.

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
