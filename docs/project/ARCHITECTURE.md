# Architecture

SplitShot is built as a local-first video analysis and export pipeline with a browser user interface backed by one project model and one controller layer.

## System Layers

| Layer | Main code | Responsibility |
| --- | --- | --- |
| Entry points | [src/splitshot/cli.py](../src/splitshot/cli.py), [src/splitshot/__main__.py](../src/splitshot/__main__.py), [src/splitshot/browser/cli.py](../src/splitshot/browser/cli.py) | Choose browser mode or runtime checks |
| Controller | [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py) | Owns the mutable `Project`, settings, and save/load actions |
| Core data | [src/splitshot/domain/models.py](../src/splitshot/domain/models.py) | Defines `Project`, ShotML settings, timing proposals, and the nested dataclasses and enums |
| Media and analysis | [src/splitshot/media/](../src/splitshot/media), [src/splitshot/analysis/](../src/splitshot/analysis) | Probe media, extract audio, detect beep and shot events |
| Presentation and scoring | [src/splitshot/timeline/](../src/splitshot/timeline), [src/splitshot/presentation/](../src/splitshot/presentation), [src/splitshot/scoring/](../src/splitshot/scoring) | Derive split rows, stage metrics, and scoring summaries |
| Merge and export | [src/splitshot/merge/](../src/splitshot/merge), [src/splitshot/export/](../src/splitshot/export) | Build merge layouts and render final video output |
| Persistence | [src/splitshot/persistence/projects.py](../src/splitshot/persistence/projects.py), [src/splitshot/config.py](../src/splitshot/config.py) | Save project bundles and app settings |
| UI surfaces | [src/splitshot/browser/](../src/splitshot/browser), [src/splitshot/ui/](../src/splitshot/ui) | Serve the browser shell and host the shared controller |

## Runtime Flow

1. A user launches `splitshot`.
2. `splitshot.cli` starts the browser server by default.
3. The controller receives media paths, probes them through `probe_video`, and stores the resulting `VideoAsset` objects in the `Project`.
4. `analyze_video_audio` extracts mono audio, runs the embedded classifier with the project's ShotML settings, and produces beep and shot events plus a normalized waveform and review suggestions.
5. Timeline and scoring helpers derive split rows, stage metrics, and scoring summaries from the project state.
6. The browser server serializes the current project with `browser_state` and serves it to the browser shell.
7. Export renders a base frame plan with FFmpeg, draws overlays, crops to the selected aspect ratio, and encodes the final file locally.

## Shared Project Model

`Project` is the main data container. It nests the following state groups:

- `primary_video` and `secondary_video` media metadata.
- `analysis` for ShotML settings, beep timing, sync offset, waveform samples, detected shots, timing-change proposals, and timing events.
- `scoring` for enabled state, ruleset, penalty counters, and hit factor.
- `overlay` for badge appearance, badge position, and custom review box settings.
- `merge` for layout, PiP sizing, and alignment offsets.
- `export` for output format, codec, crop, quality, and log capture.
- `ui_state` for browser selection state.

The persistence layer writes a bundle directory that contains `project.json` plus copied media when browser-session paths need to be preserved.

## Browser Surface

The browser server in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py) exposes a small JSON API and static assets. The key routes are:

- `GET /api/state` for the current serialized project state.
- `GET /api/practiscore/session/status`, `POST /api/practiscore/session/start`, and `POST /api/practiscore/session/clear` for the visible manual PractiScore login flow backed by a reusable persistent browser profile.
- `GET /api/practiscore/matches` and `POST /api/practiscore/sync/start` for the remote PractiScore match-list and selected-match import surface.
- `GET /media/primary` and `GET /media/secondary` for media playback.
- `POST /api/files/primary`, `POST /api/files/secondary`, and `POST /api/files/merge` for imports.
- `POST /api/project/*`, `POST /api/analysis/shotml-*`, `POST /api/analysis/shotml/*`, `POST /api/shots/*`, `POST /api/scoring/*`, `POST /api/overlay`, `POST /api/merge`, and `POST /api/export` for edits and export.

The browser shell keeps its own view state, but all authoritative data still lives in the controller and `Project` model.

### Browser Static Module Architecture

The frontend static assets (`src/splitshot/browser/static/`) have been modularized into ES modules:

```
static/
  app.js                  # Bootstrap — 26 imports, delegates to module factories
  index.html              # Shell HTML with module script tag
  styles.css              # @import loader (5 split files)
  lib/                    # Shared backbone modules (11 files)
    api.js                # API client with stale-request tracking
    store.js              # In-memory state container
    event-bus.js          # Pub/sub event bus
    layout.js             # Layout resize/apply/persist
    keys.js               # Keyboard shortcut handler
    shell-runtime.js      # Central render() and wireEvents()
    global-compat.js      # Legacy page-global bridge installer
    utils.js              # Shared DOM and math helpers
    activity.js           # Activity logging
    processing.js         # Processing bar state
    waveform-state.js     # Waveform viewport math
  components/             # Reusable UI components (4 files)
    status-bar.js         # Header, stats, timing summary
    video-player.js       # Video stage rendering
    waveform.js           # Waveform canvas + interaction
    overlay-canvas.js     # Overlay frame scheduler
  panes/                  # Pane modules (12 files)
    pane-base.js          # Generic expand/collapse base
    scoring-pane.js       # Scoring workbench
    settings-pane.js      # Settings defaults
    metrics-pane.js       # Metrics display/export
    project-pane.js       # Project + PractiScore import
    merge-pane.js         # Merge source management
    export-pane.js        # Export controls
    review-pane.js        # Review text boxes
    overlay-pane.js       # Live overlay + ShotML controls
    shotml-pane.js        # ShotML threshold/proposals
    markers-pane.js       # Popup bubble markers
    timing-pane.js        # Timing events/splits
  styles/                 # Split CSS modules (5 files)
    theme.css             # CSS variables + element base styles
    layout.css            # Shell grid, rail, status bar, resize handles
    components.css        # Video stage, overlays, waveform, inspector
    panes.css             # Pane-specific styles
    widgets.css           # Responsive breakpoints + container queries
```

Pane modules import only the generic `pane-base.js` — no pane imports another pane. Shared behavior flows through backbone modules.

The PractiScore session foundation lives in [src/splitshot/browser/practiscore_profile.py](../src/splitshot/browser/practiscore_profile.py), [src/splitshot/browser/practiscore_session.py](../src/splitshot/browser/practiscore_session.py), and the desktop runtime in [src/splitshot/browser/practiscore_qt_runtime.py](../src/splitshot/browser/practiscore_qt_runtime.py). SplitShot opens a visible app-owned Qt WebEngine window for manual PractiScore authentication, stores the persistent profile under the app data directory, and never collects PractiScore credentials through SplitShot form fields.

**Last updated:** 2026-05-06
**Referenced files last updated:** 2026-05-06
