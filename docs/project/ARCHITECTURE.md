# Architecture

<!-- Documentation reviewed: 2026-08-11 -->

SplitShot is a local-first video analysis and export system with one shared `Project` model, one controller layer, and one browser-first UI shell.

## Start Here

Read these files first if you need to understand how the app hangs together:

1. [../../src/splitshot/cli.py](../../src/splitshot/cli.py)
2. [../../src/splitshot/browser/server.py](../../src/splitshot/browser/server.py)
3. [../../src/splitshot/ui/controller.py](../../src/splitshot/ui/controller.py)
4. [../../src/splitshot/domain/models.py](../../src/splitshot/domain/models.py)
5. [../../src/splitshot/browser/static/README.md](../../src/splitshot/browser/static/README.md)

## Runtime Layers

| Layer | Main code | Owns |
| --- | --- | --- |
| Entrypoints | [../../src/splitshot/cli.py](../../src/splitshot/cli.py), [../../src/splitshot/browser/cli.py](../../src/splitshot/browser/cli.py), [../../src/splitshot/__main__.py](../../src/splitshot/__main__.py) | CLI parsing, runtime selection, startup checks |
| Browser host | [../../src/splitshot/browser/server.py](../../src/splitshot/browser/server.py), [../../src/splitshot/browser/state.py](../../src/splitshot/browser/state.py) | HTTP server, JSON API, browser state serialization, activity logging |
| Shared mutation layer | [../../src/splitshot/ui/controller.py](../../src/splitshot/ui/controller.py) | Project mutations, settings, save/load, analysis dispatch, import/export coordination |
| Core model | [../../src/splitshot/domain/models.py](../../src/splitshot/domain/models.py) | Canonical project schema, enums, serialization |
| Analysis and media | [../../src/splitshot/analysis/README.md](../../src/splitshot/analysis/README.md), [../../src/splitshot/media/README.md](../../src/splitshot/media/README.md) | Audio extraction, ShotML inference, waveform data, media probe |
| Derived presentation | [../../src/splitshot/timeline/README.md](../../src/splitshot/timeline/README.md), [../../src/splitshot/presentation/README.md](../../src/splitshot/presentation/README.md), [../../src/splitshot/scoring/README.md](../../src/splitshot/scoring/README.md) | Split rows, metrics, scoring summaries, timeline displays |
| Composition and export | [../../src/splitshot/merge/README.md](../../src/splitshot/merge/README.md), [../../src/splitshot/overlay/README.md](../../src/splitshot/overlay/README.md), [../../src/splitshot/export/README.md](../../src/splitshot/export/README.md) | Merge layout, overlay rendering, final FFmpeg export |
| Persistence and config | [../../src/splitshot/persistence/README.md](../../src/splitshot/persistence/README.md), [../../src/splitshot/config.py](../../src/splitshot/config.py) | `.ssproj` bundles, app settings, folder defaults |

## End-To-End Flow

1. `splitshot` starts through `cli.py`.
2. Browser mode creates a `ProjectController` and `BrowserControlServer`.
3. The browser shell requests `/api/state` and renders the current project.
4. Media import goes through the controller, which probes assets and updates the `Project`.
5. Analysis extracts audio, detects the start beep and shots, and stores results on `project.analysis`.
6. Timeline, scoring, and presentation helpers derive split tables, metrics, and review data from the shared project state.
7. Browser requests mutate state through POST routes handled by the server and controller.
8. Export settings build the stage-local render plan. Queue executes one or more outputs, paints overlays, composes layouts, and encodes the final files with FFmpeg.

## Ownership Boundaries

- `domain.models` defines the canonical data shape. Other layers should adapt to it, not invent parallel state.
- `ui.controller` is the main mutation boundary for project state.
- `browser.server` owns HTTP and browser-facing contracts, not domain business logic.
- `browser.static/` owns view state and cockpit interaction, but the authoritative project data still comes from the controller-backed API.
- Analysis, scoring, timeline, and export helpers should remain usable outside the browser shell so scripts and tests can call them directly.

## Browser Surface

The v1.0.7 rail is, in order: `Project`, `Media`, `Compose`, `Trim`, `Score`, `Splits`, `Markers`, `Overlay`, `Review`, `Export`, `In / Out`, `Queue`, `Metrics`, `ShotML`, and `Settings`. `Export` owns FFmpeg/output settings, `In / Out` owns optional boundary media and its overlays, and `Queue` owns render execution, queue membership, batch output, and combined output.

The cockpit is bounded to the visible window. The active inspector or expanded workbench owns scrolling, while the page shell remains fixed. Video and overlay authoring use the rendered, aspect-correct video frame as their coordinate space so resizing or browser zoom does not change saved overlay geometry.

The browser server exposes:

- `GET /api/state`
- browser-session and PractiScore routes
- media playback routes
- project, analysis, scoring, overlay, merge, settings, and export POST routes

The static shell is split across:

- `lib/` for shared runtime services
- `components/` for reusable UI pieces
- `panes/` for pane-specific behavior
- `styles/` for CSS modules

Use [../../src/splitshot/browser/static/README.md](../../src/splitshot/browser/static/README.md) for the browser-shell map.

## Project Model

`Project` is the shared contract across the app. The main state groups are:

- media assets
- analysis state and timing events
- scoring state
- overlay and review text-box state
- composition and added-media state
- export state
- UI state

Selecting a project directory creates `Input/`, `CSV/`, `Markers/`, and `Output/` beside `project.json`. Later pickers start in their owned subfolder on macOS, Windows, and Linux. Selections outside the project are copied into the owned subfolder before they are attached to state. Persistence writes metadata only, stores project-local paths relative to the bundle for every stage (including inactive stages), and resolves those paths when the project opens.

## Tests And Scripts

- Validation map: [../tests/TEST_SUITE_GUIDE.md](../tests/TEST_SUITE_GUIDE.md)
- Script inventory: [../../scripts/README.md](../../scripts/README.md)
- Browser QA ownership: [browser-control-qa-matrix.md](browser-control-qa-matrix.md)

## Read This Next

- [../../src/splitshot/README.md](../../src/splitshot/README.md)
- [../tests/TEST_SUITE_GUIDE.md](../tests/TEST_SUITE_GUIDE.md)
- [../../scripts/README.md](../../scripts/README.md)
- [LIMITATIONS.md](LIMITATIONS.md)
