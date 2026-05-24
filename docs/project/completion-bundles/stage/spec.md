# Stage Specification

## Normative statement

Stage is the canonical SplitShot editing shell. Match and Performance must reuse the Stage shell family rather than define separate layout families.

## Canonical shell requirements

### Layout grammar

The Stage shell must provide:

- a persistent app rail
- a preview-dominant main content area
- a right-hand inspector for the active workflow step
- a lower detail/info pane beneath the main content
- footer order `Home` then `Settings`
- no top automation strip
- no Project-pane automation dump

### Ownership requirements

- Stage owns the shell grammar and interaction model.
- Match and Performance may reuse Stage shell primitives, but they must not create separate shell families.
- Shared shell behavior may coordinate view switching and global status only.

## Workflow order requirements

The editing flow must remain legible and ordered:

1. Project
2. PiP
3. Splits / Score
4. Overlay
5. Markers
6. Review
7. Export

Features must be placed where they logically support that flow. Moving a control to a new location is acceptable; recreating a generic automation bucket is not.

## Project and PractiScore requirements

### Project responsibilities

Project must be limited to:

- project and match setup
- project-folder selection/open/create
- PractiScore session/sync/manual fallback entry points
- primary media import entry points

### Protected PractiScore contracts

The browser state contract must preserve:

- `practiscore_session`
- `practiscore_sync`
- `practiscore_options`

The Project and Stage workflow must preserve:

- manual `Select PractiScore File`
- local `Match type`
- local `Stage #`
- local `Competitor name`
- local `Place`

### Import and default-path requirements

- The selected project folder becomes the default home for subsequent file pickers, except for primary-video import.
- `Select Primary Video` must become `Import Primary Video`.
- Primary-video import must copy the selected asset into the project Import folder and persist the project-owned media path.
- Stage export must default to the project Output folder.

## PiP requirements

- PiP media management must live in the PiP step, not in Project.
- When PiP media exists, the secondary waveform must appear beneath the primary waveform/info lane.
- Review PiP must default to enabled when PiP media exists.
- Secondary preview playback must track the primary playback rate without lag or drift.

## Review requirements

- Splits, Score, and Overlay must default to enabled in Review.
- Review must support imported-summary and custom-summary authoring inside the review text-box workflow.
- Review summary authoring must be able to represent PractiScore/app-backed fields such as stage place, classification place, and division place.
- Background, text, and opacity controls must render in the intended two-column layout.

## Marker and overlay requirements

- Marker template colors must be independent from overlay/scoring colors.
- Overlay configuration must not silently overwrite marker styling.

## Shared shell stability requirements

- The status/progress bar must remain constrained inside the top bar.
- Stage shell changes must not regress keyboard focus, responsive layout, or destructive-action confirmation.

## Stage-owned feature parity requirements

The following features must be present in the flow where they belong and must not be called complete without proof:

- Auto Trim
- Split Sync layout parity
- Stage Mix parity
- intro title cards
- custom watermark
- score-import expansion

Proof may be one of:

- owning automated tests
- screenshot or DOM artifact evidence
- explicit doc correction when a feature is deferred or descoped

## Documentation and contract requirements

Any Stage-visible shell or workflow change requires synchronized updates to:

- owning browser tests
- browser control inventory and coverage audits where affected
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- user-facing Stage and Project docs where behavior changed

## Test requirements

At minimum, Stage reset work must be backed by:

- static UI contract coverage for the shared Stage shell
- interaction coverage for the ordered editing flow
- focused regression coverage for Project import/home, PiP waveform/sync, Review defaults and summary authoring, marker styling, and top-bar status placement
- PractiScore session/sync/manual fallback coverage where impacted

## Definition of specification success

The Stage spec is satisfied only when the shell, workflow, tests, docs, and artifacts all describe the same Stage-first product model.
