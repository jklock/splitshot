# Browser Dynamic Layout And Scoring Final Audit

## Outcome

- The latest log-backed render blocker is fixed: scoring penalty inputs are created dynamically, and `renderControls()` no longer writes to `#penalties` before it exists.
- The cockpit now uses locked-by-default resize handles for the rail, inspector, and waveform. Users can unlock, resize, and reset the layout.
- The fixed `206px` waveform row was replaced with CSS-variable sizing so the video/waveform/inspector grid scales to the viewport instead of leaving dead bottom space.
- Project is the first workflow item under the logo; the obsolete Edit workflow is not present.
- Selected-shot nudge/delete controls are isolated to the Timing pane.
- Overlay badge shape, spacing, margin, color, opacity, and score colors auto-apply and persist in project state.
- Primary/secondary/project/export path fields have browse controls.
- Import/export operations keep the processing bar and verbose activity logging path.

## Scoring Model

- Scores are saved to individual shots.
- Stage penalties and preset-specific penalty fields are saved to project scoring state.
- USPSA/IPSC use hit factor: `(points - penalties) / raw time`.
- IDPA, Steel Challenge, and GPA use time-plus style summaries from raw time plus shot/field/manual penalties.
- GPA fractional scoring is supported because manual penalties now preserve floats instead of being coerced to integers.

## Validation

- `node --check src/splitshot/browser/static/app.js`
- `uv run pytest tests/test_browser_static_ui.py tests/test_browser_control.py tests/test_scoring_and_merge.py tests/test_persistence.py`
- `uv run pytest`
- `uv run splitshot --check`
- `git diff --check`

All validation passed.

## Residual Risk

- Pointer drag behavior is still validated by UI contracts and JavaScript wiring, not by a rendered browser automation stack.
- Native file browser behavior depends on OS dialog availability; the API path is tested with an injected path chooser.
