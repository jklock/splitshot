# Automate2 UI Spec

Audited against the current SplitShot repo and competitor screenshots on 2026-05-20.

## Stable Baseline Imported From `main`

This UI plan inherits a shipped baseline that already includes:

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

Current proof boundary:
- backend/source contracts are substantially present for workspaces, output profiles, library routes, and proxy routes
- current automation scenario proof is controller-level, not browser-shell proof
- browser-shell completion and packaged automation proof are still unproven
- **landing page does not exist**
- **Setup Once, Apply Everywhere workflow does not exist**
- **Performance Library analytics do not exist**

The UI completion work must overhaul the browser shell so the user can actually use:

- `Landing Page`
- `Stage Video Edit`
- `Match Video Edit`
- `Performance Library`

## Current Reality

### Already present in backend or state

- workspace CRUD and stage open/return routes
- output-profile CRUD and render-plan routes
- library browse/open/proxy routes
- angle-align, audio-mix, result-card, and stage-clip mutation routes
- expanded `/api/state` summary fields

### Still missing for a truthful UI

- landing page
- stage clip persistence, not just in-memory controller state
- a dedicated read route for stage clips
- a dedicated read route for the current angle-director plan
- Setup Once, Apply Everywhere workflow UI
- Performance Library analytics UI
- multi-track waveform UI
- color-coded segments UI
- batch export progress UI

### Validated classification

- `done` backend floor:
  - workspace model and inheritance
  - output-profile CRUD and render-plan resolution
  - library browse/open/proxy routes and summary state
- `partial` backend floor:
  - stage clip support is mutation-only and controller-local
  - PiP interaction exists but is not yet acceptable as product behavior
  - library analytics routes missing
  - archive routes missing
- `missing` for UI readiness:
  - landing page
  - stage-clip persistence
  - dedicated stage-clip read route
  - dedicated angle-director plan read route
  - Setup Once, Apply Everywhere workflow
  - Performance Library analytics
  - multi-track waveform
  - color-coded segments
  - batch export progress
- `deferred`:
  - packaged automation proof

## UI Surface Model

### Surface 1: Landing Page

The Landing Page is the user's front door.

It owns:

- three large entry cards (Stage Video Edit, Match Video Edit, Performance Library)
- recent activity tiles
- quick-start shortcuts
- welcome state for first-time users

Required UI:

- hero section with SplitShot branding
- three entry cards with icons, titles, and one-sentence descriptions
- recent activity section with thumbnails, names, dates, and actions
- quick-start buttons: "New Stage", "New Match"
- empty state with friendly message and getting-started tips

### Surface 2: Stage Video Edit

Stage Video Edit remains the deep stage editor.

It owns:

- timing
- scoring
- markers
- overlay
- review
- metrics
- ShotML
- stage output profiles
- multi-angle features

Required UI additions:

- output-profile manager with preview
- profile list
- create / duplicate / rename / delete
- active retained-review source selection
- `Trim Dead Time` editor with waveform preview
- `Shot Data on Screen` editor with preview
- `Video Shape` editor
- `Opening Title` editor with preview
- `Your Logo` editor with preview
- `Keep Shooter in Frame` placeholder/editor hooks
- `Smart Angle Switching` editor with preview
- `Line Up Angles` controls
- `Camera Jobs` editor
- `Audio Balance` controls
- `Override Smart Cuts` editor
- multi-track waveform
- color-coded segments
- render-plan preview and render-result state
- inherited/defaulted context when opened from a workspace

### Surface 3: Match Video Edit

Match Video Edit is the workspace-level editing surface.

It owns:

- workspace lifecycle
- stage grid with status
- shared defaults
- stage overrides
- stage open/return
- `Setup Once, Apply Everywhere`
- `Match Recap`
- `Stage Composite`
- batch export

Required UI additions:

- workspace create/open/save controls
- stage grid with status, missing media, overrides, and review state
- drag-and-drop reordering
- shared-default editor
- stage-override editor
- stage open action
- return-to-workspace affordance
- `Setup Once, Apply Everywhere` workflow with preview
- batch export queue with progress
- separate `Match Recap` and `Stage Composite` editors

### Surface 4: Performance Library

Performance Library is a separate browse-and-reopen surface with analytics.

It owns:

- historical records
- filters and search
- proxy state
- analytics and trends
- tagging and notes
- reopen links to stage/workspace editor contexts

Required UI additions:

- summary tiles from `library_summary`
- filter/search/sort controls
- record table
- selected-record detail view
- proxy action panel
- analytics dashboard with charts
- personal bests display
- outlier highlighting
- tag editor
- notes editor
- open proxy / refresh proxy / open stage / open workspace actions
- export library data actions

## Shell Architecture

### New shell requirements

The shell must expose a top-level surface switcher for:

- `Landing Page`
- `Stage Video Edit`
- `Match Video Edit`
- `Performance Library`

The shell must also show persistent context:

- active project or workspace name
- active stage name when relevant
- editing mode: standalone stage vs workspace stage vs library browsing
- return-to-workspace availability
- output/proxy/render status

### Landing Page behavior

- shown on app start when no recent project is open
- shown when user clicks "Home" or SplitShot logo
- never blocks access to editors
- recent activity updates in real-time

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

Those tools should remain as mode-aware panes under the correct parent surface, especially within `Stage Video Edit`.

## UI-Enabling Backend Follow-Up

This package assumes the backend is mostly complete, but the UI work requires a narrow support pass.

Required additions:

- persist stage clips and clip-local angle/audio/cut state
- add a dedicated stage-clip read route
- add a dedicated angle-director plan read route
- add landing page API routes
- add analytics API routes
- add archive API routes

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

## Stage Video Edit UI Contract

### Required layout

Stage Video Edit should present:

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
- configure multi-angle features
- preview all output settings on the video

## Match Video Edit UI Contract

### Required workspace layout

Match Video Edit should present:

- workspace header with match info
- stage grid
- workspace-level defaults and status
- editor tabs or sections for:
  - stages
  - `Setup Once, Apply Everywhere`
  - `Match Recap`
  - `Stage Composite`
  - batch export

### Required stage grid fields

- stage display name
- stage number
- completeness status
- missing media
- override present
- last reviewed
- drag handle for reordering

### Required Setup Once, Apply Everywhere flow

1. User configures Stage 1
2. User returns to match grid
3. UI detects Stage 1 has configuration
4. UI shows "Apply Stage 1's settings to all other stages?" button
5. User clicks button
6. UI shows preview of changes
7. User confirms
8. UI applies settings and updates grid
9. Grid shows "shared" badges on updated stages

### Required Batch Export controls

- select all / select none
- per-stage checkbox
- output recipe selector
- start export button
- export queue with progress bars
- cancel buttons
- completion summary

### Required Match Recap controls

- stage inclusion/exclusion
- stage order visibility
- result-card configuration
- match-scope profile render action
- preview before render

### Required Stage Composite controls

- clip list
- add/update/remove clip
- camera job assignment
- line-up trigger/result state
- audio balance
- override smart cuts
- composite render action
- preview before render

## Performance Library UI Contract

### Required layout

- summary tiles (total stages, matches, personal bests, recent activity)
- filters/search row
- record table
- selected-record detail panel
- proxy status and actions
- analytics dashboard
- tag and notes panel

### Required analytics

- trend charts (line charts for metrics over time)
- personal bests list
- outlier highlights
- discipline breakdown
- stage-to-stage comparison tool

### Required states

- empty library
- stale proxy
- missing proxy
- missing archive
- unresolved reopen target
- successful reopen target

## Proof And Release Contract

The UI package must drive:

- browser inventory updates
- targeted UI suites
- browser E2E
- packaged proof
- release-note and changelog naming checks if shipping

The UI work is not complete until the new shell structure, PiP playback smoothness, and the four product surfaces are all proven.
