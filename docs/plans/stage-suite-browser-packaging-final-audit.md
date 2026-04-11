# Stage Suite, Browser Control, and Packaging Final Audit

## Scope

This pass covered:

- Stage1-4 local detector CSV output for Shot Streamer comparison.
- Browser-based local control interface.
- Video toolchain validation.
- Source/repo packaging path with browser-default one-command launch.
- Feature-focused tests for the new work.

References used:

- Python standard library HTTP server documentation: https://docs.python.org/3/library/http.server.html
- PyInstaller spec-file and binary/data bundling documentation: https://pyinstaller.org/en/stable/spec-files.html
- Qt for Python deployment documentation: https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html

## Benchmark Output

Generated file:

- `artifacts/stage_suite_analysis.csv`

Command:

```bash
uv run splitshot-benchmark-csv --output artifacts/stage_suite_analysis.csv Stage1.MP4 Stage2.MP4 Stage3.MP4 Stage4.MP4
```

Summary:

| Stage | Beep | Draw | Raw Time | Shots | Avg Split |
|---|---:|---:|---:|---:|---:|
| Stage1 | 9.586 | 2.012 | 13.541 | 18 | 0.678 |
| Stage2 | 2.108 | 2.182 | 19.899 | 19 | 0.984 |
| Stage3 | 7.956 | 1.773 | 13.633 | 18 | 0.698 |
| Stage4 | 3.588 | 1.845 | 16.944 | 18 | 0.888 |

The screenshot `Raw` column is the benchmark metric. SplitShot exports this as `raw_time_s`; `stage_time_s` is retained as a compatibility alias for the same beep-to-final-shot duration.

Reference raw times from the screenshot:

| Stage | Reference Raw | SplitShot Raw | Delta |
|---|---:|---:|---:|
| Stage1 | 13.55 | 13.552 | +0.002 |
| Stage2 | 19.83 | 19.826 | -0.004 |
| Stage3 | 13.62 | 13.624 | +0.004 |
| Stage4 | 17.01 | 17.013 | +0.003 |

## Browser Control Audit

Implemented:

- `splitshot-web` CLI command.
- Localhost-only default bind at `127.0.0.1`.
- Static browser UI with Shot Streamer-style rail, metrics, preview, waveform, split cards, merge controls, overlay controls, scoring controls, project controls, layout controls, and export controls.
- JSON API backed by the same `ProjectController` used by the desktop app.
- Primary import with automatic analysis.
- Secondary import with automatic sync.
- Local media serving with byte-range support for browser video playback.
- Waveform click-to-add shot and shift-click-to-move-beep browser interactions.
- Selected-shot nudge, delete, score assignment, and save/open/export controls.

Validation:

- `tests/test_browser_control.py` verifies state serialization after automatic ingest and API import/edit/score behavior.
- `uv run splitshot-web --help` returns the browser CLI help successfully.

Known constraint:

- Browser mode is a separate local control surface, not a live mirror of an already-open desktop window. It uses the same backend and project file format, but a desktop session and a browser session are independent processes unless the same saved project is opened.

## Video Toolchain Audit

Implemented:

- `splitshot.media.ffmpeg.resolve_media_binary()` now checks bundled resources before falling back to `PATH`.
- Runtime supports `SPLITSHOT_FFMPEG_DIR` for explicit bundled-toolchain testing/builds.
- Packaged lookup paths are platform-aware:
  - `splitshot/resources/ffmpeg/macos/ffmpeg`
  - `splitshot/resources/ffmpeg/macos/ffprobe`
  - `splitshot/resources/ffmpeg/windows/ffmpeg.exe`
  - `splitshot/resources/ffmpeg/windows/ffprobe.exe`

Validation command:

```bash
uv run python scripts/validate_toolchain.py
```

Result:

- `ffmpeg` resolved to `/opt/homebrew/bin/ffmpeg`.
- `ffprobe` resolved to `/opt/homebrew/bin/ffprobe`.
- Browser assets were present.
- Packaging scripts/spec were present.
- `hdiutil` was present for local macOS DMG creation.

## Packaging Audit

Implemented:

- Browser-first source command: `uv run --python 3.12 splitshot`.
- Secondary desktop command: `uv run --python 3.12 splitshot --desktop`.
- Runtime check command: `uv run --python 3.12 splitshot --check`.
- Compatibility aliases: `splitshot-web` and `splitshot-desktop`.
- `packaging/splitshot.spec` for PyInstaller.
- `packaging/build_macos.sh` for `.app` plus `.dmg`.
- `packaging/build_windows.ps1` for Windows `.exe` bundle.
- `packaging/README.md` documenting FFmpeg/FFprobe placement and native platform build flow.
- `pyproject.toml` optional `package` extra with PyInstaller.
- Browser assets and packaged runtime resources are included in wheel/build configuration.

Packaging readiness:

- The app is now runnable from the repo/package with one primary command.
- FFmpeg/FFprobe can be bundled rather than requiring end-user install.
- Native `.dmg` and `.exe` artifacts are no longer part of the immediate delivery target.

Not completed in this local pass:

- No actual `.dmg` or `.exe` artifact was produced because that is no longer required for this pass.
- Code signing, Apple notarization, installer branding, icons, and auto-update are not implemented yet.
- FFmpeg redistribution licensing review is still required before public release.

## Application Feature Audit

Validated by automated tests:

- ML-backed analysis emits beep, shot, waveform, and confidence data.
- Detection threshold changes shot detection behavior.
- Stage1 real benchmark tracks the Shot Streamer screenshot within test tolerances and matches the confirmed stage time closely.
- Primary upload runs automatic analysis.
- Secondary upload runs automatic sync.
- Split rows, draw time, stage time, and average split are computed.
- Desktop loaded-review UI switches from upload state to review state.
- Split-card selection drives selected shot state.
- Project save/load preserves media, waveform, shots, scoring, overlay, merge, and export state.
- Merge layouts cover side-by-side, above/below, and PiP.
- Scoring calculates hit factor with penalties.
- Export writes MP4 and preserves crop/layout behavior.
- Browser control imports, edits, scores, and returns project state.
- Benchmark CSV writes the comparison data needed for Stage1-4.
- FFmpeg resolver prefers bundled/configured binaries.

Full test result:

```text
31 passed
```

Desktop smoke result:

```text
app-smoke-ok
```

## Remaining Risks

- Accuracy beyond Stage1-4 is still a data problem. More real match videos and Shot Streamer comparison exports are needed before claiming broad production parity.
- Browser UI covers the control workflow, but it is not yet pixel-for-pixel identical to the desktop UI.
- Packaging scripts need to be executed on both target operating systems with actual bundled FFmpeg binaries before release.
- Signed/notarized distribution is not yet addressed.
