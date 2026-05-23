# Technical Architecture

This document maps the automation plan onto the current SplitShot architecture.

## Existing Architecture To Reuse

Current reusable seams:

- `src/splitshot/domain/models.py`
- `src/splitshot/persistence/projects.py`
- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/browser/server.py`
- `src/splitshot/browser/static/`
- `src/splitshot/export/`

These should remain the foundation rather than introducing a second disconnected architecture.

## Required Architecture Additions

### 1. Domain model expansion

Need explicit domain objects for:

- stage records with stable ids
- match workspaces with stage membership and shared defaults
- output variants
- library records
- retained proxies

### 2. Persistence expansion

Need persistence support for:

- match workspace state
- stage override state
- output-variant state
- library metadata and index storage
- retained proxy metadata

The project persistence layer should remain authoritative for editable workspace truth.
Performance Library persistence can be a separate store layered beside project bundles.

### 3. Controller orchestration

The controller should own:

- stage vs match workspace mutation flows
- inheritance resolution
- output-variant generation
- library record refresh
- retained proxy refresh orchestration

### 4. Browser state and routes

Browser state must evolve to expose:

- current editor scope: single or multi
- current match workspace context
- inherited vs overridden setting state
- output variants per stage or match
- library record previews and retrieval state

Browser routes need support for:

- opening a stage from a match workspace
- returning to the match workspace
- library browsing and record playback
- output-variant creation and retrieval

### 5. Export pipeline

The export pipeline should be extended, not replaced.

It must support:

- named output variants
- review proxy generation
- Lead-In Card and Brand Mark recipe layers
- ratio-aware export variants
- later Subject Track Crop support
- stage-scope and match-scope exports

### 6. Library indexing subsystem

Need a library indexing layer responsible for:

- ingesting reviewed stage and match truth
- writing normalized metric rows
- updating historical records
- linking retained proxies and outputs

### 7. Background refresh/update path

Need background-style orchestration for:

- keeping library records current
- rebuilding stale proxies
- avoiding UI-blocking refresh chains

The initial implementation may still run locally and synchronously at key commit points, but the architecture should reserve a background-refresh seam.

## Proposed Ownership By Subsystem

### Domain models

Own:

- ids
- hierarchy
- inheritance-capable schemas
- output and proxy metadata structures

### Persistence

Own:

- bundle serialization for editable stage and match truth
- library serialization for historical records and metric indexes
- migration compatibility for older project formats

### Controller

Own:

- truth mutation
- scope transitions
- library refresh triggers
- proxy generation requests

### Browser state/server

Own:

- route model
- state serialization
- editor scope transitions
- library browsing APIs

### Browser UI

Own:

- Single vs Multi workspace UX
- inherited vs overridden state presentation
- output-variant management surfaces
- library record browsing and playback entrypoints

### Export pipeline

Own:

- stage and match export generation
- review proxy generation
- output recipe realization

## Packaged-app Impact

The packaged desktop app must prove:

- output variants work in built artifacts
- retained proxy generation works with packaged media tools
- library playback can resolve retained proxies inside packaged runs
- no workflow depends on host-installed tools or local-only fixtures

## Acceptance Criteria

- The architecture can support three surfaces without duplicating editing truth.
- Existing controller/browser/export foundations remain reusable.
- Performance Library is technically separate but still tied cleanly to editor truth.

## Concrete Architecture Contract

### Domain layer

- Keep `Project` as the stage editor contract.
- Add a separate `MatchWorkspace` model and related records rather than overloading `Project`.
- Add dedicated models for:
  - `StageEntry`
  - `OutputProfile`
  - `LibraryStageRecord`
  - `LibraryMatchRecord`
  - `LibraryOutputRecord`
  - `RetainedProxyRecord`

### Persistence layer

- Extend `src/splitshot/persistence/projects.py` only for stage-bundle compatibility concerns.
- Add a new persistence module for match workspaces.
- Add a separate persistence module for library records and indexes.
- Keep save/load responsibilities separated:
  - stage bundle persistence owns `project.json`
  - workspace persistence owns `workspace.json`
  - library persistence owns `~/.splitshot/library/`

### Controller layer

The controller remains the orchestration owner for:

- opening and saving stage bundles
- opening and saving workspaces
- resolving inherited settings
- mutating stage overrides
- triggering library refresh
- triggering retained proxy refresh

The controller must not push this orchestration into browser-only logic.

### Browser server layer

The browser server must remain the HTTP contract owner.

Additive route families:

- `/api/workspace/*`
- `/api/output-profiles/*`
- `/api/library/*`
- `/api/proxy/*`

The existing `/api/project/*` routes remain valid for single-stage operations.

### Browser state layer

`browser_state(...)` remains the single serialization seam for `/api/state`.

It must expand to serialize:

- editor scope
- workspace context
- inherited-setting origin
- output-profile collections
- library summaries
- retained-proxy freshness

### Export layer

The export pipeline remains the rendering owner for:

- stage output profiles
- match recap outputs
- stage composite outputs
- retained review-video generation

It must not become the source of truth for stage metrics or stage analysis.

## Exact API Contract Additions

### Workspace routes

- `/api/workspace/new`
- `/api/workspace/open`
- `/api/workspace/save`
- `/api/workspace/stage/add`
- `/api/workspace/stage/remove`
- `/api/workspace/stage/open`
- `/api/workspace/stage/return`
- `/api/workspace/defaults`
- `/api/workspace/stage/override`
- `/api/workspace/stage/override/reset`

### Output profile routes

- `/api/output-profiles/list`
- `/api/output-profiles/create`
- `/api/output-profiles/update`
- `/api/output-profiles/delete`
- `/api/output-profiles/render`

### Library routes

- `/api/library/list`
- `/api/library/filter`
- `/api/library/stage/open`
- `/api/library/match/open`

### Proxy routes

- `/api/proxy/refresh`
- `/api/proxy/status`
- `/api/library/proxy/open`

## Required Validation Rules

- Every mutating route must validate stable ids before writing.
- Every successful mutating route must save the affected persistence layer before returning.
- Browser state must never report a workspace stage entry without a corresponding status.
- Route failures must return structured errors rather than silent no-ops.

## Backward-Compatibility Contract

- current stage-only routes remain supported
- current `project.json` bundles remain supported
- current app and folder settings remain supported
- new workspace and library subsystems are additive

## Required Tests And Proof

- route coverage for every new workspace, output-profile, library, and proxy path
- browser state serialization coverage for new scope/context keys
- persistence coverage for stage bundle, workspace bundle, and library store isolation
- export coverage for stage profile render, match recap render, and stage composite render

## Code Clarity And Non-Regression Contract

### Required implementation shape

The future code must preserve:

- one stage-truth model
- one browser-state serialization seam
- one controller orchestration owner for persisted mutations
- additive route families instead of route replacement for legacy stage behavior

### Legacy route non-regression expectations

The following route families are frozen compatibility surfaces unless this package explicitly extends them:

- `/api/project/*`
- `/api/export`
- `/api/export/settings`
- `/api/export/preset`
- `/api/state`

Extending the automation package must not silently change the meaning of those existing routes for single-stage flows.

### Existing export non-regression expectations

The implementation must preserve:

- current single-stage export viability
- current preset-driven export behavior for legacy stage workflows
- current media/probe assumptions used by packaged exports

### Packaged-app non-regression expectations

The implementation must preserve:

- no host-tool dependency for packaged behavior
- no local-only fixture dependency for packaged audits or validation
- previously proven packaged launch, backend-ready, and visible workflow flows
