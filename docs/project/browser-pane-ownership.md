# Browser Pane Ownership

Audit basis: modularization commits `f14cd41` and `ac05392`, plus the current browser shell/backend wiring.

## Pane owners

- `Project`: project lifecycle, PractiScore import controls, project drafts, PractiScore/video detection summary.
- `Review`: review playback state and review visibility state.
- `Splits / Timing`: split rows, timing event editing, timing workbench state.
- `Score`: scoring workbench, imported PractiScore scoring reference.
- `Markers`: popup and marker authoring.
- `Overlay`: overlay styling, placement, drag, and preview controls.
- `PiP / Merge`: merge media list, source controls, merge preview, merge-source commits.
- `Export`: export preset rendering, export drafts, export log surface.
- `Metrics`: metrics workbench, graphs, metrics exports.
- `ShotML`: ShotML defaults, proposals, and proposal actions.
- `Settings`: settings sections, settings summaries, and section save/reset payload building.

## Shell ownership

`src/splitshot/browser/static/app.js` remains responsible for:

- bootstrapping pane modules
- shared shell state and runtimes
- generic route helpers
- media, waveform, and layout runtimes
- top-level render orchestration

Pane-owned summaries and section-owned settings payloads should stay out of the shell.
