# Full Browser E2E QA Plan

This is the execution plan for taking SplitShot from partial browser control coverage to a truthful full-control end-to-end QA claim.

It does not replace [browser-control-coverage-plan.md](browser-control-coverage-plan.md). That file is the exhaustive control inventory. This file defines the closure rules, sequencing, fixtures, and exit gates required before anyone can honestly say that every mutable browser control is covered.

## Non-Negotiable Rules

- Do not mark a mutable control complete on presence, smoke, or static coverage alone.
- Do not count a Python-only contract test as browser QA for a browser control.
- Do not count a preview-only assertion if the control also changes saved project state, defaults, or export output.
- Do not mark a pane complete until every mutable control in that pane is either `direct-e2e` or explicitly waived as low risk with a written reason.
- Do not claim full-app coverage while any stateful control remains `missing`, `smoke`, or `static` in the inventory plan.

## Coverage Tiers

| Tier | Meaning | Allowed for final full-coverage claim |
| --- | --- | --- |
| `missing` | No direct browser test for the control. | Never. |
| `static` | The control only has presence, selector, or layout coverage. | Never for mutable controls. |
| `smoke` | The control can be opened or clicked, but its downstream effect is not proven. | Only for low-risk navigation-only controls such as section headers if they do not change persisted state. |
| `direct-behavior` | A browser test manipulates the real control and proves the immediate state or API mutation. | Only for controls whose effects stop at the same pane and do not persist or affect export/render. |
| `direct-e2e` | A browser test manipulates the real control, proves the immediate mutation, proves the downstream impact, and proves the relevant persistence or render path. | Required for every mutable control that affects project state, timing, scoring, overlay, markers, merge, export, settings, or ShotML. |

## Per-Control Definition Of Done

A mutable control is not done until one browser test proves all applicable items below:

1. The exact visible control is manipulated in the browser UI.
2. The immediate DOM, app state, or API payload mutation is asserted.
3. The downstream effect is asserted in the consuming surface.
4. The change survives rerender, reload, reopen, or defaults reload when that control is persisted.
5. The rendered or exported outcome is asserted when the control affects preview, overlay, PiP, markers, or export output.
6. Destructive and reversible controls cover both apply and rollback paths.
7. The inventory and QA matrix are updated in the same change so the coverage claim stays honest.

## Shared Fixtures And Helpers Required Up Front

Before closing the remaining gap clusters, lock the fixture layer so coverage work does not drift into flaky one-off tests.

| Fixture or helper | Why it is required | Expected home |
| --- | --- | --- |
| Stable primary synthetic video fixture | Fast deterministic timing, scoring, waveform, overlay, and marker coverage. | Existing browser fixtures plus `synthetic_video_factory` helpers. |
| Stable PractiScore-backed project fixture | Required for Project, Score, imported summary, Review, and Settings-default capture coverage. | `tests/browser` or `tests/artifacts` fixture helpers. |
| Stable merge fixture with one extra video and one still image | Required for PiP defaults, per-card controls, and export parity. | `tests/browser` fixture helpers. |
| Real render verification fixture | Required to prove export-facing controls beyond payload-only assertions. | `example_data` plus one short reference bundle. |
| Browser helper for reload and reopen | Required to prove persisted browser, project, and settings state. | Shared browser helper module. |
| Export artifact inspection helper | Required to assert width, height, codec, duration, and rendered overlay/PiP presence. | `tests/export` or shared helper module. |
| DOM inventory audit | Required so new controls cannot land without an owner row and test target. | New inventory audit test under `tests/browser`. |

## Execution Phases

### Phase 0: Lock The Truth Boundary

Goal: remove the loopholes that allow unowned controls or weak coverage to be counted as done.

Work:

- Add a browser control inventory audit that parses the browser shell and fails if a mutable control is not represented in the inventory plan.
- Add a coverage manifest or table that maps each mutable control family to its owning browser test file.
- Separate navigation-only controls from stateful controls so `smoke` cannot be used to hide state gaps.
- Standardize shared browser helpers for reload, reopen, export assertion, file picking, and color-picker interaction.

Exit gate:

- Every mutable control in the browser shell has an owner row.
- Every owner row names the target test file.
- CI can fail when a new control appears without an owner.

### Phase 1: Shared Shell And Drag/Layout Interactions

Goal: finish the shell controls that gate the entire app and convert the remaining smoke-only items into direct behavior or direct E2E coverage.

Surfaces:

- rail tool buttons
- settings gear
- rail collapse toggle
- layout lock toggle
- rail resize handle
- waveform resize handle
- sidebar resize handle
- waveform reset and mode controls
- primary video player surface hooks

Required downstream assertions:

- active pane changes correctly
- localStorage and project UI state persist correctly
- shell layout restores after reload or reopen
- selected waveform mode and viewport state stay consistent after shell changes

Primary test targets:

- extend `tests/browser/test_browser_rail_layout.py`
- extend `tests/browser/test_browser_interactions.py`
- add `tests/browser/test_browser_shell_e2e.py`

Exit gate:

- No shell control that changes state remains `smoke`.
- Drag and resize behavior is covered with persistence assertions, not just geometry snapshots.

### Phase 2: Splits And Score End-To-End Closeout

Goal: take Splits and Score from partial interaction coverage to full row-action and downstream-metric coverage.

Surfaces:

- timing event kind, label, and position controls
- add-event and remove-event flows
- selected-shot nudge and delete flows
- timing workbench row actions
- scoring enable, preset, row selection, score, penalties, delete, and restore

Required downstream assertions:

- `split_rows`, `timing_segments`, and `scoring_summary` update correctly
- Metrics reflects the new timing and scoring state
- Overlay and Review consumers reflect first-shot and score changes where applicable
- saved project reopen restores the mutated timing and scoring state

Primary test targets:

- extend `tests/browser/test_timing_waveform_contracts.py`
- extend `tests/browser/test_scoring_metrics_contracts.py`
- extend `tests/browser/test_browser_interactions.py`

Exit gate:

- Every mutable Splits and Score control is `direct-e2e`.
- Manual timing events have add, move-position, and delete coverage.

### Phase 3: Markers, Review, Overlay, And Color Picker

Goal: close the largest remaining browser-surface gap and prove authoring controls all the way through preview and render.

Surfaces:

- compact marker controls, workbench open/close, playback window, loop, and previous/next navigation
- shot-linked marker cards and time-marker cards
- markers workbench actions
- popup template controls
- popup bubble card controls, including motion editing
- review text-box source, stack lock, placement, size, colors, opacity, and stage drag
- overlay timer, draw, score anchors, locks, typography, badge styles, and live box sizing
- color picker modal controls and swatches

Required downstream assertions:

- marker selection seeks the correct time or shot
- preview updates immediately and survives rerender
- saved project reopen restores marker, overlay, and review state
- export render reflects the same marker, overlay, review, and color choices shown in the browser

Primary test targets:

- add `tests/browser/test_markers_e2e.py`
- add `tests/browser/test_overlay_review_e2e.py`
- add `tests/browser/test_color_picker_modal.py`
- extend `tests/browser/test_overlay_review_contracts.py`

Exit gate:

- No popup, review, overlay, or color-picker control remains `missing`.
- Preview parity and export parity are proven for at least one marker-heavy fixture and one review-heavy fixture.

### Phase 4: PiP, Merge, Export Settings, And Export Log

Goal: cover the remaining merge and export controls all the way into a rendered artifact.

Surfaces:

- merge enable toggle, layout, size, X, Y defaults
- per-source merge card collapse, remove, size, opacity, X, Y, and sync nudges
- export quality, aspect ratio, size, frame rate, codecs, bitrates, color space, FFmpeg preset, two-pass
- export log modal close, backdrop, and log-export actions

Required downstream assertions:

- merge preview matches control changes before export
- export payload contains the intended merge and encoding state
- rendered artifact matches expected geometry, codec pair, duration, and visible PiP placement
- export log actions work after a real export run

Primary test targets:

- extend `tests/browser/test_merge_export_contracts.py`
- add `tests/browser/test_merge_e2e.py`
- add `tests/browser/test_export_settings_e2e.py`
- extend `tests/export/test_export.py`

Exit gate:

- Every merge and export setting control is `direct-e2e`.
- At least one real rendered export covers video plus still-image PiP.

### Phase 5: Settings And ShotML Full Coverage

Goal: prove that defaults and detector tuning controls are not just present but actually drive new-project behavior and rerun behavior.

Surfaces:

- all Settings collapsible headers
- global template scope, landing pane, reopen-last-tool, import current, reset defaults
- scoring, PiP, overlay, markers, export, and ShotML defaults
- ShotML section toggles and all numeric or boolean detector fields
- ShotML rerun, reset, proposal generation, and proposal apply or discard actions

Required downstream assertions:

- new project creation picks up the chosen defaults
- project or app scope separation is preserved
- ShotML rerun changes timing or proposal output as expected
- changed defaults and ShotML values survive reopen where intended and reset cleanly where intended

Primary test targets:

- add `tests/browser/test_settings_e2e.py`
- add `tests/browser/test_shotml_e2e.py`
- extend `tests/analysis/test_analysis.py`
- extend `tests/browser/test_browser_control.py`

Exit gate:

- No mutable Settings or ShotML control remains `smoke` or `static`.
- Each defaults family has at least one test that proves it changes a fresh project, not just the current form values.

### Phase 6: Cross-Surface Final Truth Gate

Goal: verify the app as a whole, not just pane-by-pane slices.

Required end-to-end scenarios:

1. Create or open a project, import PractiScore, adjust timing, edit scores, save, reload, and verify persistence.
2. Add and edit markers, review boxes, and overlay settings, then render an export and confirm preview or export parity.
3. Add PiP media, tune merge settings, export, and confirm rendered placement and sync.
4. Change global defaults, create a fresh project, and verify the new project starts with the chosen defaults.
5. Change ShotML settings, rerun analysis, apply or discard proposals, and confirm downstream timing changes.

Primary test targets:

- add `tests/browser/test_browser_full_app_e2e.py`
- add one short real-render regression suite under `tests/export`

Exit gate:

- Every mutable control family has a direct owner test.
- Every pane has at least one full scenario that crosses pane boundaries.
- One real render suite passes on representative assets before claiming readiness.

## Honest Reporting Rules

Use the inventory and matrix with the following hard rules:

- `full-control QA coverage` means zero mutable controls are left at `missing`, `static`, or `smoke`.
- `covered` means `direct-e2e` unless the control is purely navigation-only.
- `smoke` and `static` remain gap states, not completion states, for mutable controls.
- If a control only has preview coverage but no persistence or export proof, it is not end to end.
- If a control affects export and only the request payload is asserted, it is not end to end.

## Immediate Work Queue

Start with the biggest gap clusters in this order:

1. Markers, Review, Overlay, and the color picker modal.
2. PiP and Export settings, including real rendered output checks.
3. Settings defaults and all ShotML numeric sections.
4. Remaining shell navigation and rail-collapse persistence gaps.
5. Final cross-surface scenario tests that bind the panes together.

Do not mark the repo as fully covered until all five items above are closed and the Phase 6 gate is passing.

**Last updated:** 2026-04-24
**Referenced files last updated:** 2026-04-24