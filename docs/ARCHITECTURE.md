# Architecture

SplitShot is built as a local-first video analysis and export pipeline with a browser user interface backed by one project model and one controller layer.

## System Layers

| Layer | Main code | Responsibility |
| --- | --- | --- |
| Entry points | [src/splitshot/cli.py](../src/splitshot/cli.py), [src/splitshot/__main__.py](../src/splitshot/__main__.py), [src/splitshot/browser/cli.py](../src/splitshot/browser/cli.py) | Choose browser mode or runtime checks |
| Controller | [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py) | Owns the mutable `Project`, settings, and save/load actions |
| Core data | [src/splitshot/domain/models.py](../src/splitshot/domain/models.py) | Defines `Project` and the nested dataclasses and enums |
| Media and analysis | [src/splitshot/media/](../src/splitshot/media), [src/splitshot/analysis/](../src/splitshot/analysis) | Probe media, extract audio, detect beep and shot events |
| Presentation and scoring | [src/splitshot/timeline/](../src/splitshot/timeline), [src/splitshot/presentation/](../src/splitshot/presentation), [src/splitshot/scoring/](../src/splitshot/scoring) | Derive split rows, stage metrics, and scoring summaries |
| Merge and export | [src/splitshot/merge/](../src/splitshot/merge), [src/splitshot/export/](../src/splitshot/export) | Build merge layouts and render final video output |
| Persistence | [src/splitshot/persistence/projects.py](../src/splitshot/persistence/projects.py), [src/splitshot/config.py](../src/splitshot/config.py) | Save project bundles and app settings |
| UI surfaces | [src/splitshot/browser/](../src/splitshot/browser), [src/splitshot/ui/](../src/splitshot/ui) | Render the browser shell and host the shared controller |

## Runtime Flow

1. A user launches `splitshot`.
2. `splitshot.cli` starts the browser server by default.
3. The controller receives media paths, probes them through `probe_video`, and stores the resulting `VideoAsset` objects in the `Project`.
4. `analyze_video_audio` extracts mono audio, runs the embedded classifier, and produces beep and shot events plus a normalized waveform.
5. Timeline and scoring helpers derive split rows, stage metrics, and scoring summaries from the project state.
6. The browser server serializes the current project with `browser_state` and serves it to the static frontend.
7. Export renders a base frame plan with FFmpeg, draws overlays in Qt, crops to the selected aspect ratio, and encodes the final file locally.

## Shared Project Model

`Project` is the main data container. It nests the following state groups:

- `primary_video` and `secondary_video` media metadata.
- `analysis` for beep timing, sync offset, waveform samples, detected shots, and timing events.
- `scoring` for enabled state, ruleset, penalty counters, and hit factor.
- `overlay` for badge appearance, badge position, and custom review box settings.
- `merge` for layout, PiP sizing, and alignment offsets.
- `export` for output format, codec, crop, quality, and log capture.
- `ui_state` for browser selection state.

The persistence layer writes a bundle directory that contains `project.json` plus copied media when browser-session paths need to be preserved.

## Browser Surface

The browser server in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py) exposes a small JSON API and static assets. The key routes are:

- `GET /api/state` for the current serialized project state.
- `GET /media/primary` and `GET /media/secondary` for media playback.
- `POST /api/files/primary`, `POST /api/files/secondary`, and `POST /api/files/merge` for imports.
- `POST /api/project/*`, `POST /api/shots/*`, `POST /api/scoring/*`, `POST /api/overlay`, `POST /api/merge`, and `POST /api/export` for edits and export.

The browser frontend keeps its own view state, but all authoritative data still lives in the controller and `Project` model.

## Runtime Artifacts

- Settings are stored in `~/.splitshot/settings.json`.
- Browser activity logs are written under `logs/` by default.
- Benchmark CSV output is written to `artifacts/` when requested.

## Design Constraints

The codebase is intentionally local-first. It does not depend on a remote service for detection, scoring, merge math, or export rendering. The main external dependencies are FFmpeg, FFprobe, NumPy, and PySide6.

**Last updated:** 2026-04-13
**Referenced files last updated:** 2026-04-13
