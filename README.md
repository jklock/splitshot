<p align="center">
	<img src="src/splitshot/browser/static/githublogo.png" alt="SplitShot logo" width="800" />
</p>

# SplitShot

SplitShot is a local-first browser app for competition shooting video analysis, split timing, scoring, PiP review, overlay tuning, metrics, and final video export.

<img src="docs/screenshots/ProjectPane.png" alt="SplitShot browser app showing the Project pane and video review workspace" width="1000">

## What SplitShot Can Do

- Import a local stage video and keep the whole workflow on your machine. SplitShot works directly from files on disk, so you can load match footage, reopen saved projects, and keep your training and match videos out of the cloud.
- Detect the timer beep and shot events from the video's audio with a local analysis pass. SplitShot builds an initial shooting timeline for you instead of making you mark every shot by hand from scratch.
- Review and correct split timing in the waveform editor. You can inspect the detected events, adjust bad markers, add missing timing events, remove false positives, and make the timeline match what actually happened on the run.
- Score the run manually or load PractiScore context for the same stage. That gives you a fast path whether you are doing ad hoc review, building a stage breakdown from memory, or aligning the video with official stage and competitor context.
- Tune on-video shot badges, timer badges, score summaries, and review text boxes with live preview feedback. You can control what appears on the video, how it is styled, and how much analysis detail the finished clip should surface to the viewer.
- Add PiP, SbS, and UaB media such as a second angle or still images. SplitShot lets you bring in supporting visuals, place them where they belong, and use them to clarify positions, transitions, makeup shots, or stage design details.
- Review derived metrics, then export CSV or text summaries. The app turns the corrected timeline and scoring data into usable output for post-stage review, coaching notes, spreadsheets, or sharing outside the app.
- Render a finished local video with FFmpeg. Your final export can include the corrected timing, overlays, review annotations, PiP media, and presentation choices you made during analysis.

## Install SplitShot

SplitShot runs from source or as an Electron desktop app. You need `uv`, `ffmpeg`, and the browser you already use.

### Prerequisites

- **`uv`:** [docs.astral.sh/uv/getting-started/installation](https://docs.astral.sh/uv/getting-started/installation/)
- **FFmpeg:** [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
- **Git:** [git-scm.com/downloads](https://git-scm.com/downloads)

### Source Install (All Platforms)

```bash
git clone https://github.com/jklock/splitshot.git
cd splitshot
uv python install 3.12
uv sync
uv run splitshot
```

If the browser does not open automatically, retry with `uv run splitshot --no-open` and open the URL shown in the terminal manually.

Optional check:

```bash
uv run splitshot --check
```

### Electron Desktop App (macOS)

The Electron build produces a signed, notarized macOS DMG. See [docs/project/ELECTRON_RELEASE.md](docs/project/ELECTRON_RELEASE.md) for the signing and release workflow.

### CLI Options

```bash
uv run splitshot                          # Default: browser mode with Qt desktop runtime
uv run splitshot --headless               # HTTP server only, no Qt window
uv run splitshot --no-open                # Start server without opening browser
uv run splitshot --host 0.0.0.0 --port 8765  # Custom bind address/port
uv run splitshot --project /path/to/project.ssproj  # Open project at startup
uv run splitshot --log-level info         # Mirror activity log to terminal
uv run splitshot --check                  # Validate toolchain and assets
```

## Basic Workflow

1. Open SplitShot in your browser.
2. Select the primary video, or paste a direct local path and press Enter for very large files.
3. Wait for local analysis to detect the beep and shots.
4. Fix timing in Splits before you score or style anything.
5. Import PractiScore if you want official stage context.
6. Use Score, Overlay, and Review to set the scoring and on-video presentation.
7. Add PiP media if you want a second angle or supporting images.
8. Export the final video.

## App Guides

- [Project](docs/userfacing/panes/project.md)
- [Splits](docs/userfacing/panes/splits.md)
- [Score](docs/userfacing/panes/score.md)
- [ShotML](docs/userfacing/panes/shotml.md)
- [PiP](docs/userfacing/panes/pip.md)
- [Markers](docs/userfacing/panes/popup.md)
- [Overlay](docs/userfacing/panes/overlay.md)
- [Review](docs/userfacing/panes/review.md)
- [Settings](docs/userfacing/panes/settings.md)
- [Export](docs/userfacing/panes/export.md)
- [Metrics](docs/userfacing/panes/metrics.md)

## More Documentation

- [Full user guide](docs/userfacing/USER_GUIDE.md)
- [Workflow guide](docs/userfacing/workflow.md)
- [Troubleshooting](docs/userfacing/troubleshooting.md)
- [Documentation hub](docs/README.md)
- [Current limitations](docs/project/LIMITATIONS.md)
- [Electron release and signing](docs/project/ELECTRON_RELEASE.md)
- [Contributing](CONTRIBUTING.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Security](SECURITY.md)

## License

SplitShot is licensed under the MIT License. See [LICENSE](LICENSE).
