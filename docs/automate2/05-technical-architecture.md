# Technical Architecture

This document defines the technical architecture for SplitShot v2.

## Principles

1. **Local-first**: All data stays on the user's machine.
2. **Analysis-first**: Truth is derived, reviewed, and preserved before any output.
3. **One truth, many outputs**: A single reviewed record produces many exports.
4. **Setup once, apply everywhere**: Match editing should be fast through inheritance.
5. **Layman-friendly**: The UI must be understandable without domain expertise.

## System Layers

```
┌─────────────────────────────────────────────┐
│           Browser Shell (UI)                │
│  Landing Page │ Stage │ Match │ Library    │
├─────────────────────────────────────────────┤
│           Browser State/API                 │
│  /api/state │ /api/workspace │ /api/library│
├─────────────────────────────────────────────┤
│           Controller Layer                  │
│  Project │ Workspace │ Library │ Export    │
├─────────────────────────────────────────────┤
│           Domain Layer                      │
│  Models │ Metrics │ Analysis │ Scoring     │
├─────────────────────────────────────────────┤
│           Persistence Layer                 │
│  Project Bundles │ Workspace │ Library DB  │
├─────────────────────────────────────────────┤
│           Pipeline Layer                    │
│  Detection │ Export │ Proxy │ Archive     │
├─────────────────────────────────────────────┤
│           External Tools                    │
│  ffmpeg │ ffprobe │ ShotML                  │
└─────────────────────────────────────────────┘
```

## Browser Shell

The browser shell is the user's entire view of SplitShot.

Responsibilities:
- render the Landing Page
- render Stage Video Edit with all tool panes
- render Match Video Edit with stage grid and shared settings
- render Performance Library with browsing, playback, and analytics
- handle all user input and route it to the API layer
- maintain local UI state (selections, drafts, expansions)
- provide smooth preview playback with bounded drift correction

Key components:
- `index.html` — the single-page app shell
- `app.js` — the main application runtime
- `lib/shell-runtime.js` — surface switching and navigation
- `lib/api.js` — HTTP client for backend routes
- `lib/store.js` — reactive state store
- `lib/event-bus.js` — component communication
- `components/video-player.js` — primary and secondary video playback
- `components/waveform.js` — waveform rendering and interaction
- `components/overlay-canvas.js` — live overlay rendering
- `panes/*.js` — tool pane implementations

## Browser State and API

The API layer exposes:

- `/api/state` — full application state snapshot
- `/api/project/*` — single-stage project CRUD
- `/api/workspace/*` — match workspace CRUD
- `/api/library/*` — Performance Library browse and open
- `/api/output-profiles/*` — output profile CRUD and render
- `/api/render/*` — export and proxy rendering
- `/api/analytics/*` — Performance Library analytics

State contract:
- `/api/state` is summary-oriented
- heavy or per-surface data is fetched through dedicated routes
- do not preload all clip or library record detail into the poll payload
- state updates are pushed via Server-Sent Events or polled

## Controller Layer

The controller layer owns:

- `ProjectController` — stage-level truth mutations
- `WorkspaceController` — match workspace mutations
- `LibraryController` — library record mutations and queries
- `ExportController` — export pipeline orchestration
- `ProxyController` — proxy generation and invalidation
- `ArchiveController` — compressed video generation
- `AnalyticsController` — analytics computation and caching

Each controller:
- validates mutations against domain rules
- persists changes to the correct storage
- triggers downstream updates (e.g., library refresh after project save)
- returns structured errors, not exceptions

## Domain Layer

The domain layer owns:

- `Project` — stage truth model
- `Workspace` — match workspace model
- `LibraryRecord` — historical record model
- `OutputProfile` — output variant model
- `ProxyRecord` — retained proxy model
- `ArchiveRecord` — compressed video model
- `AnalyticsRecord` — pre-computed analytics model
- `MetricComputation` — shot timing and score computation
- `ScoringEngine` — ruleset-aware scoring

Domain rules:
- models are plain data objects, not ORM entities
- validation lives in the domain, not the controller
- models must be serializable to JSON deterministically

## Persistence Layer

The persistence layer owns:

- `ProjectStore` — project bundle read/write
- `WorkspaceStore` — workspace bundle read/write
- `LibraryStore` — library record and index read/write
- `IndexStore` — metric index and search catalog
- `SettingsStore` — app-level settings

Storage layout:
- project bundles: user-chosen folders
- workspace bundles: user-chosen folders
- library: `~/.splitshot/library/`
- settings: `~/.splitshot/settings.json`

Concurrency:
- file writes are atomic (write temp, then rename)
- no database locking; last-write-wins for user edits
- background tasks (proxy generation) must not block foreground saves

## Pipeline Layer

The pipeline layer owns:

- `DetectionPipeline` — beep and shot detection
- `ExportPipeline` — video export with overlays
- `ProxyPipeline` — lightweight review proxy generation
- `ArchivePipeline` — compressed video generation
- `AnalyticsPipeline` — metric computation and trend analysis

Pipeline rules:
- pipelines are asynchronous and cancellable
- progress is reported to the UI
- failures are logged and surfaced to the user
- pipelines must not modify source media

### Export Pipeline Architecture

The export pipeline supports:

- single-stage export
- batch stage export
- match recap export
- stage composite export

Each export:
1. resolves output profile settings
2. resolves inheritance (stage override > match shared > first-stage snapshot > global)
3. computes overlay frames
4. runs ffmpeg with computed settings
5. writes output to project/workspace Output folder
6. reports progress and completion

### Proxy Pipeline Architecture

The proxy pipeline:
1. detects when truth hash has changed
2. resolves the retained-review source output profile
3. generates a lightweight MP4 at reduced resolution
4. stores in `~/.splitshot/library/proxies/`
5. updates the library record

### Archive Pipeline Architecture

The archive pipeline:
1. triggered by explicit user action or scheduled policy
2. generates a compressed MP4 at 480p-720p
3. stores in `~/.splitshot/library/archives/`
4. updates the library record

## External Tools

SplitShot depends on:

- `ffmpeg` — video processing, export, proxy, archive generation
- `ffprobe` — media inspection
- ShotML model — shot detection inference

These must be available on PATH at runtime.

## Performance Requirements

- UI must remain responsive during analysis (detection runs in a subprocess)
- Waveform rendering must sustain 60fps during zoom and pan
- Video preview must play smoothly with bounded drift correction
- Library queries must return in under 500ms for 10,000 records
- Analytics charts must render in under 1 second
- Export progress must update at least every 2 seconds

## Security Considerations

- All data is local; no network transmission of user content
- Library paths are relative or inside `~/.splitshot`
- No execution of user-provided commands
- File inputs are validated before processing

## Extension Points

Future extensions should use these seams:

- new output profiles: add fields to `OutputProfile` model and export pipeline
- new analytics: add `AnalyticsRecord` types and computation functions
- new disciplines: add scoring rulesets to `ScoringEngine`
- new camera roles: add to `AngleRoles` enum and UI

## Acceptance Criteria

- All layers can be tested independently.
- The UI can be developed against mock API responses.
- The domain layer has no dependency on the UI or external tools.
- Persistence can be swapped for in-memory stores in tests.
- Pipelines can be cancelled without corrupting output files.
