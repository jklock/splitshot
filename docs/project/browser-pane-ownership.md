# Browser Pane Ownership

Audit basis: current browser shell/backend wiring plus the released `docs/v107` Phase 14 corrective packet on `2026-06-23`.

## Pane owners

- `Project`: project lifecycle, project drafts, PractiScore import source, imported stage selector for context lookup, `match-stage-number`, `match-competitor-name`, `match-competitor-place`, and the compact imported summary rows `Name`, `Place`, `Match Time`, `Division`.
- `Media`: stage list, per-stage collapse state, stage file rows, file intake, primary designation, file removal, and `Edit Stage` live-stage entry.
- `Compose`: composition-only controls for the active stage.
- `Trim`: active-stage trim and sync controls only.
- `Review`: review playback state, review visibility state, and imported summary presentation.
- `Queue`: queue state review, queue membership/state, batch processing, combined processing, and `Edit Stage` navigation back to `Media`.
- `Splits / Timing`: split rows, timing event editing, timing workbench state.
- `Score`: scoring workbench and imported PractiScore scoring reference.
- `Markers`: popup and marker authoring.
- `Overlay`: overlay styling, placement, drag, and preview controls.
- `Export`: stage-local export settings only; no direct render execution surface.
- `Metrics`: metrics workbench, graphs, metrics exports.
- `ShotML`: ShotML defaults, proposals, and proposal actions.
- `Settings`: settings sections, settings summaries, and section save/reset payload building.

## Explicit non-owners

- `Project` does not own stage media/file intake, stage file rows, primary designation, file removal, stage edit entry, queue review/process UI, or helper prose for downstream workflow panes.
- `Media` does not own competitor identity selectors already wired through `Project`.
- `Compose` does not own media intake/removal after the Phase 14 correction.
- `Queue` does not own filler workflow copy and must not route `Edit Stage` into `Compose`.

## Shell ownership

`src/splitshot/browser/static/app.js` remains responsible for:

- bootstrapping pane modules
- shared shell state and runtimes
- generic route helpers
- media, waveform, and layout runtimes
- top-level render orchestration

Pane-owned summaries and section-owned settings payloads should stay out of the shell.
