# Architecture

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
8. Export builds a render plan, paints overlays, composes merge layouts, and encodes the final file with FFmpeg.

## Ownership Boundaries

- `domain.models` defines the canonical data shape. Other layers should adapt to it, not invent parallel state.
- `ui.controller` is the main mutation boundary for project state.
- `browser.server` owns HTTP and browser-facing contracts, not domain business logic.
- `browser.static/` owns view state and cockpit interaction, but the authoritative project data still comes from the controller-backed API.
- Analysis, scoring, timeline, and export helpers should remain usable outside the browser shell so scripts and tests can call them directly.

## Browser Surface

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
- merge and composition state
- export state
- UI state

Persistence writes `project.json` plus copied browser-session media when needed to keep bundle reopen behavior stable.

## Tests And Scripts

- Validation map: [../tests/TEST_SUITE_GUIDE.md](../tests/TEST_SUITE_GUIDE.md)
- Script inventory: [../../scripts/README.md](../../scripts/README.md)
- Browser QA docs:
  [browser-control-qa-matrix.md](browser-control-qa-matrix.md),
  [browser-control-coverage-plan.md](browser-control-coverage-plan.md),
  [browser-full-e2e-qa-plan.md](browser-full-e2e-qa-plan.md)

## Read This Next

- [../../src/splitshot/README.md](../../src/splitshot/README.md)
- [../tests/TEST_SUITE_GUIDE.md](../tests/TEST_SUITE_GUIDE.md)
- [../../scripts/README.md](../../scripts/README.md)
- [LIMITATIONS.md](LIMITATIONS.md)
