# Browser Usability Logging Waveform Final Audit

## Log Review

- Before implementation, no existing activity log files were present.
- After adding logging, generated run logs confirmed server initialization, GET/POST activity, API starts/successes, file ingest, shot edits, overlay/scoring changes, sync changes, browser activity events, and shutdown.
- The smoke-test log confirmed `/api/activity` records browser-originated UI events into the same per-run file.

## UI Quality Audit

- Removed the always-visible Open Stage Video, Add Second Angle, and Refresh commands from the sidebar.
- Removed the bottom left rail New button.
- Kept project creation and file selection contextual to the Project pane.
- Kept secondary video selection contextual to Project and Merge.
- Added a thin top status strip containing only filename and metrics.
- Moved metrics out of the sidebar.
- Brightened and strengthened rail labels.
- Enlarged the logo to fill the rail brand cell while staying clipped inside its container.
- Scoped selected-shot controls to review, timing, edit, and scoring contexts instead of showing them on every page.
- Preserved the center priority of video first and waveform second.

## Waveform Quality Audit

- Changed waveform default interaction from accidental add-shot to explicit Select mode.
- Added explicit Add Shot and Move Beep modes.
- Added expanded waveform mode that hides the inspector and gives the waveform most of the workspace.
- Added shot labels with times on the expanded waveform.
- Added selected-shot highlighting.
- Added shot list buttons under expanded waveform.
- Added pointer drag to move selected shots.
- Added keyboard left/right nudge and delete/backspace delete.

## Timing Quality Audit

- Added expanded timing mode that hides the inspector and turns the center workspace into a timing table.
- Timing rows still select shots and share the selected-shot edit controls.

## Observability Audit

- Server logging writes JSONL records to terminal and `logs/splitshot-browser-*.log`.
- Browser logging writes to the browser console and `/api/activity`.
- `logs/` is gitignored so verbose run logs do not dirty the repository.

## Validation

- `node --check src/splitshot/browser/static/app.js`
- `uv run --python 3.12 pytest tests/test_browser_static_ui.py tests/test_browser_control.py`
- `uv run --python 3.12 pytest`
- Browser usability smoke check verified removed duplicate controls, top strip order, video -> waveform -> inspector order, and `/api/activity` file logging.

## Residual Risk

- Full pointer behavior is still validated by wiring and API tests, not a real browser automation runner. The next testing upgrade should add a browser-level E2E dependency if the project accepts that toolchain.
