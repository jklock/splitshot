# Browser Functional Button Trace Final Audit

## Button/Page Trace

| Page | Control | Expected effect | Validation |
| --- | --- | --- | --- |
| Project | Open Primary Video | Opens local path picker, imports selected path, analyzes beep/shots, switches to Review | JS contract + `/api/import/primary` browser API tests |
| Project | Primary path Enter | Imports typed path and analyzes | JS contract |
| Project | Add Second Angle | Opens local path picker, imports secondary path, computes sync, switches to Merge | JS contract + `/api/import/secondary` browser API tests |
| Project | Project Browse/Save/Open/Delete/New | Uses local `.ssproj` path and project API routes | browser API tests and persistence tests |
| Review | Split cards | Select shot and update selected state | `/api/shots/select` covered through browser API tests |
| Review | Threshold | Auto-applies detection threshold | static contract + API route coverage |
| Waveform | Select/Add Shot/Move Beep/drag/arrows/delete | Mutates shot/beep timing in milliseconds | browser shot edit API tests and waveform wiring tests |
| Timing | Expand/Collapse | Moves timing editor into main workspace | static UI contract tests |
| Timing | Nudge/Delete | Mutates selected shot or removes it | browser shot edit API tests |
| Scoring | Enable/Preset/Penalties/Score letter | Saves shot scores and scoring penalties, updates summary | scoring API tests |
| Scoring | Set Score Position | Arms video click for selected shot score placement | scoring position API tests |
| Overlay | Position/size/style/colors | Auto-applies preview/export overlay state | overlay API tests, persistence tests, export pixel test |
| Merge | Add Second Angle/Layout/PiP/Sync/Flip | Enables merge, adjusts sync/layout, swaps media | merge/sync/swap API tests |
| Layout | Quality/aspect/crop/export composition | Auto-applies export layout state | export settings API tests |
| Layout | Unlock/Reset Layout | Enables and resets rail/inspector/waveform resizing | static resize contract tests |
| Export | Preset/settings/path/export | Writes local MP4 and stores FFmpeg log/errors | browser `/api/export` MP4 test |

## Fixes

- Primary/secondary video controls are now one-step local actions instead of Browse + Import + Choose.
- Selecting a local primary or secondary path from the file browser immediately imports/analyzes it.
- Typed primary/secondary paths import on Enter.
- The floating score placement button was removed from the video surface and moved into Scoring.
- Live overlay timer/draw/score badges now use tabular numbers and fixed minimum widths so adjacent badges do not shift as time changes.
- Export overlay rendering now honors badge style type, spacing, and margin.
- Browser export is now functionally tested through `/api/export`, not only through the lower-level export pipeline.
- Export overlay is tested by reading a rendered MP4 frame and asserting overlay-colored pixels are present.

## Validation

- `node --check src/splitshot/browser/static/app.js`
- `uv run pytest tests/test_browser_static_ui.py tests/test_browser_control.py tests/test_export.py`
- `uv run pytest`
- `uv run splitshot --check`
- `git diff --check`

All validation passed.
