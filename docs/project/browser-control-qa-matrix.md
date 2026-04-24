# Browser Control QA Matrix

This matrix is the source of truth for browser-visible controls and their current QA coverage.

It is not a claim that every button or field has its own direct behavior test. Rows marked `static`, `smoke`, or `presence-only` are still gaps that should be upgraded when those controls change.

## How To Use This

Before changing a browser control, find its row here and update the matching tests in the same change.

If a control is missing from this matrix, it does not have an explicit owner yet.

## Matrix

| Surface | Controls in scope | Direct tests | Downstream impact tests | Coverage |
| --- | --- | --- | --- | --- |
| Shared shell | left rail buttons, settings gear, rail collapse toggle | [tests/browser/test_browser_static_ui.py](../../tests/browser/test_browser_static_ui.py), [tests/browser/test_browser_rail_layout.py](../../tests/browser/test_browser_rail_layout.py) | active tool switching, rail collapse persistence | smoke + static |
| Project / import | project details, choose/open project, primary import, PractiScore import, delete project | [tests/browser/test_project_lifecycle_contracts.py](../../tests/browser/test_project_lifecycle_contracts.py), [tests/browser/test_browser_control.py](../../tests/browser/test_browser_control.py) | project.json round-trip, imported context, destructive flow safety | behavioral |
| Score | score pane header, Edit, Collapse, enable scoring, preset select, score letter select, penalties, restore, delete | [tests/browser/test_browser_rail_layout.py](../../tests/browser/test_browser_rail_layout.py), [tests/browser/test_browser_control.py](../../tests/browser/test_browser_control.py), [tests/browser/test_scoring_metrics_contracts.py](../../tests/browser/test_scoring_metrics_contracts.py) | scoring summaries, overlay score text, export state | behavioral + smoke |
| Splits / waveform | timing edit, selected shot actions, add/delete/move/nudge, waveform expand/zoom/amplitude, waveform pan | [tests/browser/test_timing_waveform_contracts.py](../../tests/browser/test_timing_waveform_contracts.py), [tests/browser/test_browser_control.py](../../tests/browser/test_browser_control.py), [tests/browser/test_browser_interactions.py](../../tests/browser/test_browser_interactions.py) | split rows, waveform selection, zoom persistence, metrics inputs, drag movement | behavioral + interaction |
| Markers / Review / Overlay | show overlay checkbox, badge size, style, locks, color pickers, text boxes, popup editor, text-box drag | [tests/browser/test_overlay_review_contracts.py](../../tests/browser/test_overlay_review_contracts.py), [tests/browser/test_browser_control.py](../../tests/browser/test_browser_control.py), [tests/browser/test_browser_interactions.py](../../tests/browser/test_browser_interactions.py), [tests/browser/test_browser_static_ui.py](../../tests/browser/test_browser_static_ui.py) | preview/export parity, overlay visibility, review box creation, drag cleanup, stack lock behavior | behavioral + interaction + static |
| Settings | scope, default tool, import current, reset defaults, section collapse, template fields | [tests/browser/test_browser_static_ui.py](../../tests/browser/test_browser_static_ui.py), [tests/browser/test_browser_control.py](../../tests/browser/test_browser_control.py) | reset defaults only; individual field behavior is not directly tested | smoke + static |
| Metrics | expand/collapse, export CSV/text | [tests/browser/test_scoring_metrics_contracts.py](../../tests/browser/test_scoring_metrics_contracts.py), [tests/browser/test_browser_static_ui.py](../../tests/browser/test_browser_static_ui.py) | metrics row model, CSV/text output | behavioral + static |
| Export | output path, preset, quality, export modal/log | [tests/browser/test_merge_export_contracts.py](../../tests/browser/test_merge_export_contracts.py), [tests/browser/test_browser_control.py](../../tests/browser/test_browser_control.py), [tests/export/test_export.py](../../tests/export/test_export.py) | FFmpeg args, export log, output artifacts | behavioral |
| ShotML | threshold, rerun, proposal generation, reset defaults | [tests/browser/test_browser_static_ui.py](../../tests/browser/test_browser_static_ui.py), [tests/browser/test_browser_control.py](../../tests/browser/test_browser_control.py), [tests/analysis/test_analysis.py](../../tests/analysis/test_analysis.py) | detection, proposals, defaults persistence | behavioral + analysis |

## Known Gaps

- This matrix does not yet give every individual field a dedicated end-to-end test.
- The browser interaction file covers waveform expand/zoom/amplitude, waveform pan and shot movement, overlay visibility and badge toggles, and review text-box creation and drag.
- The Settings row is the clearest example: most fields are presence-tested, while reset defaults has direct behavior coverage.
- Some rows are still mostly static or smoke coverage; those are the first candidates for stronger behavior tests.
- When a browser control regresses, update the matrix row and the test in the same change so the coverage claim stays honest.