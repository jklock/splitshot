# Browser Dynamic Layout And Scoring Plan

## Goal

Make the browser cockpit behave like a local editing tool instead of a static page:

- The viewport must always scale without leaving a dead bottom bar.
- Video and waveform are the primary work surfaces.
- The right inspector only shows controls for the active tool.
- Layout panes start locked, can be unlocked, resized, and reset.
- Imports and exports show processing status.
- Every button/control activity remains logged to console and per-run log files.
- Scoring must be explicit: scores and penalties are saved to stage/shot data and feed the selected scoring ruleset.

## Required Changes

1. Move Project to the top of the left rail immediately after the logo.
2. Remove the obsolete Edit mode from the workflow.
3. Keep selected-shot controls only in the Timing pane.
4. Pin the waveform canvas to the top of the waveform area and remove empty dead space.
5. Add a locked-by-default layout resize model for the rail, inspector, and waveform.
6. Add an unlock/reset layout control with activity logging.
7. Fix the render crash from dynamic scoring penalty inputs.
8. Shrink color inputs and overlay style controls.
9. Remove no-video overlay text that can cover split content.
10. Keep overlay changes auto-applied.
11. Provide browse/import buttons for path-based inputs.
12. Keep `uv run splitshot` as the documented launch path without requiring `--python 3.12`.

## Validation

- Browser static tests must verify UI contracts and button wiring.
- Browser API tests must verify file import, scoring, overlay, export, project, and path behavior.
- JavaScript syntax must pass `node --check`.
- Full pytest suite must pass.
- Runtime check must pass with `uv run splitshot --check`.
