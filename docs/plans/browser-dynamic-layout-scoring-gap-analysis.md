# Browser Dynamic Layout And Scoring Gap Analysis

## Log Findings

- Latest browser logs show server requests succeeded, then the browser reported `null is not an object (evaluating '$("penalties").value = state.project.scoring.penalties')`.
- That exception happens during `render()`, so unrelated buttons appear broken because state updates fail after the API response.
- The fixed `206px` waveform row and fixed minimum video row can leave unused black viewport space at some browser sizes.

## UI Gaps

- The left rail is close to the desired structure, but Project must be the first workflow item and the rail text must stay bold/readable.
- The selected-shot nudge/delete controls are correctly a Timing concept and should not leak into other tools.
- The waveform expansion exists, but normal mode still allocates fixed height and does not expose user-controlled resizing.
- Color inputs and overlay controls consume too much inspector space.
- The Project and Export path fields have browse support; import path buttons must remain wired and tested.

## Functional Gaps

- Scoring is per-shot plus stage-level penalty fields:
  - USPSA/IPSC use hit factor from shot points minus penalties divided by raw time.
  - IDPA/GPA/Steel style presets use raw time plus configured penalty adders.
- Overlay style changes should auto-apply without a separate apply button.
- Import/export operations need visible status and verbose log output for diagnosis.

## Closure Plan

- Remove the dynamic-penalty render crash.
- Add layout state, lock/unlock, reset, and resize handlers.
- Convert fixed layout rows/columns to CSS variables and viewport-safe grid constraints.
- Tighten inspector controls and tests around active panes.
- Update tests so they fail if buttons are unlogged, unwired, or if the fixed row regression returns.
