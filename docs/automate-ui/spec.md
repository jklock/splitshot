# Automate UI Spec

Audited against the merged `automate` branch on 2026-05-20 after importing `main` at `v1.0.5`.

## Stable Baseline Imported From `main`

This UI plan no longer starts from a pre-release browser shell. It inherits a shipped baseline that already includes:

- Windows-safe overlay font policy for exports
- browser preview font-stack alignment to released Windows-safe families
- packaged Windows OCR proof for exported overlay readability
- `docs/Clip1.MP4` fixture validation in workflow and packaged-test lanes

Nothing in this package may weaken those guarantees.

## Summary

The automation backend is largely present:

- workspace routes exist
- library routes exist
- proxy routes exist
- output-profile routes exist
- controller/state support exists for most automation concepts

The browser shell does not yet expose that system as a coherent product.

The UI completion work must overhaul the browser shell so the user can actually use:

- `Single Video`
- `Multi Video`
- `Performance Library`

The highest-priority blocker is PiP preview smoothness. Today, added third-person or extra-video preview playback is too jumpy to sync visually because the preview path hard-seeks too aggressively during live playback.

## Current Reality

### Already present in backend or state

- workspace CRUD and stage open/return routes
- output-profile CRUD and render-plan routes
- library browse/open/proxy routes
- angle-align, audio-mix, result-card, and stage-clip mutation routes
- expanded `/api/state` summary fields:
  - `editor_scope`
  - `active_match_id`
  - `active_stage_id`
  - `return_to_match_available`
  - `match_workspace_summary`
  - `workspace_stage_entries`
  - `workspace_shared_defaults`
  - `workspace_override_summary`
  - `output_profiles`
  - `library_summary`

### Still missing for a truthful UI

- stage clip persistence, not just in-memory controller state
- a dedicated read route for stage clips
- a dedicated read route for the current angle-director plan
- a shell navigation model built around the three product surfaces
- first-class UI for output profiles
- first-class UI for workspaces
- first-class UI for Performance Library
- PiP playback smoothness fit for visual sync work

## UI Surface Model

### Surface 1: Single Video

Single Video remains the deep stage editor.

It owns:

- timing
- scoring
- markers
- overlay
- review
- metrics
- ShotML
- stage output profiles

Required UI additions:

- output-profile manager
- profile list
- create / duplicate / rename / delete
- active retained-review source selection
- `Run Window` editor
- `Metric Captions` editor
- `Frame Profiles` editor
- `Lead-In Card` editor
- `Brand Mark` editor
- `Subject Track Crop` placeholder/editor hooks
- render-plan preview and render-result state
- inherited/defaulted context when opened from a workspace

### Surface 2: Multi Video

Multi Video is the workspace-level editing surface.

It owns:

- workspace lifecycle
- stage table
- shared defaults
- stage overrides
- stage open/return
- `Match Recap`
- `Stage Composite`

Required UI additions:

- workspace create/open/save controls
- stage grid with status, missing media, overrides, and review state
- shared-default editor
- stage-override editor
- stage open action
- return-to-workspace affordance
- separate `Match Recap` and `Stage Composite` editors

### Surface 3: Performance Library

Performance Library is a separate browse-and-reopen surface.

It owns:

- historical records
- filters and search
- proxy state
- reopen links to stage/workspace editor contexts

Required UI additions:

- summary tiles from `library_summary`
- filter/search/sort controls
- record table
- selected-record detail view
- proxy action panel
- open proxy / refresh proxy / open stage / open workspace actions

## Shell Architecture

### New shell requirements

The shell must expose a top-level surface switcher for:

- `Single Video`
- `Multi Video`
- `Performance Library`

The shell must also show persistent context:

- active project or workspace name
- active stage name when relevant
- editing mode: standalone stage vs workspace stage vs library browsing
- return-to-workspace availability
- output/proxy/render status

### Existing shell behavior to retire

The current flat rail of:

- Project
- PiP
- Score
- Splits
- Markers
- Overlay
- Review
- Export
- Metrics
- ShotML

must stop serving as the top-level product structure.

Those tools should remain as mode-aware panes under the correct parent surface, especially within `Single Video`.

## UI-Enabling Backend Follow-Up

This package assumes the backend is mostly complete, but the UI work requires a narrow support pass.

Required additions:

- persist stage clips and clip-local angle/audio/cut state
- add a dedicated stage-clip read route
- add a dedicated angle-director plan read route

Design rule:

- keep `/api/state` summary-oriented
- fetch heavy or per-surface data through dedicated routes
- do not preload all clip or library record detail into the poll payload

## PiP Playback Smoothness Contract

### Problem definition

Current PiP preview sync uses frequent drift checks and hard-seeks preview media when drift exceeds a small threshold.

This applies to:

- the classic secondary preview path
- the merge-preview item path

Result:

- third-person preview playback is jumpy
- users cannot visually sync by eye
- drag/adjustment work becomes useless because the preview itself does not move smoothly

### Required sync strategy

The UI overhaul must switch preview sync to a two-tier model:

- small drift:
  - bounded playback-rate correction only
- large drift:
  - one hard seek, then resume continuous playback

Hard seek is allowed only for:

- initial attach
- manual scrub
- play/pause boundary
- explicit sync nudge
- large drift breach
- source or metadata reset

### Required drag strategy

During active PiP drag:

- suspend heavy video reseek work
- suspend full overlay recompute
- keep updates local and RAF-driven
- cache frame geometry at drag start
- commit final position on pointerup or debounced settle
- do not call route commits on every pointermove

### PiP proof requirement

The implementation is not complete until proof shows:

- no per-frame reseek churn during steady playback
- smooth enough preview for by-eye sync
- no route churn during drag
- no broken final sync or position state after commit

## Single Video UI Contract

### Required layout

Single Video should present:

- a stage context header
- a primary editing stack
- a right-side or secondary panel set for:
  - output profiles
  - export/render status
  - inherited/defaulted workspace context when applicable

### Required user flows

- create and manage output profiles
- preview render plan before render
- choose retained-review source profile
- render output profiles
- stay inside one stage truth record even when multiple outputs exist

## Multi Video UI Contract

### Required workspace layout

Multi Video should present:

- workspace header
- stage table
- workspace-level defaults and status
- editor tabs or sections for:
  - stages
  - `Match Recap`
  - `Stage Composite`

### Required stage table fields

- stage display name
- stage number
- completeness status
- missing media
- override present
- last reviewed

### Required Stage Composite controls

- clip list
- add/update/remove clip
- angle role assignment
- angle-align trigger/result state
- audio mix lanes
- cut override editor
- composite render action

### Required Match Recap controls

- stage inclusion/exclusion
- order visibility
- result-card configuration
- match-scope profile render action

## Performance Library UI Contract

### Required layout

- summary tiles
- filters/search row
- record table
- selected-record detail panel
- proxy status and actions

### Required states

- empty library
- stale proxy
- missing proxy
- unresolved reopen target
- successful reopen target

## Proof And Release Contract

The UI package must drive:

- browser inventory updates
- targeted UI suites
- browser E2E
- packaged proof
- release-note and changelog naming checks if shipping

The UI work is not complete until the new shell structure, PiP playback smoothness, and the three product surfaces are all proven.
