# Browser Project + Waveform Flow Final Audit

## Scope

This pass fixed the latest browser workflow issues: a separate misaligned waveform/timeline layer and Project controls that did not behave like durable local-file actions.

## Changes

- Waveform: removed the standalone `timeline-strip` layer. The waveform canvas is now the only visual timing surface for scale, beep markers, shot markers, selected regions, zoom, and hit-testing.
- Project buttons: `Open Project` now opens a `.ssproj` file dialog. `Save Project` saves to the current path or opens a save dialog when no path exists. `Browse` chooses a project save path.
- Project state: browser state now includes the active project path so the Project pane reflects actual persisted state.
- Media durability: missing media paths are marked unavailable instead of leaving stale video in the browser. The client now resets video elements on project changes or missing media.
- Display names: server fallback strips browser-session UUID prefixes so saved/reopened projects do not expose generated temp names.

## Validation

- `node --check src/splitshot/browser/static/app.js`
- `uv run pytest tests/test_browser_static_ui.py tests/test_browser_control.py::test_browser_path_dialog_endpoint_supports_project_open_and_save tests/test_browser_control.py::test_browser_project_open_replaces_stale_media_state tests/test_browser_control.py::test_browser_state_marks_missing_project_media_unavailable`
- `uv run pytest tests/test_browser_static_ui.py tests/test_browser_control.py`
- `uv run pytest`
- `git diff --check`

Result: full suite passed with `65 passed`.

## Residual Risk

The hidden browser upload endpoint still exists for compatibility, but the visible Project workflow now uses local OS path selection so saved projects reference durable local paths instead of temporary browser-upload session files.
