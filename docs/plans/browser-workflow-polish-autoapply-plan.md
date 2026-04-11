# Browser Workflow Polish And Auto-Apply Plan

## Log Review

Reviewed the latest browser activity logs before changes.

- Project navigation is logged but appears after the main workflow tools, making project setup harder to find.
- Review-pane shot cards can select and delete shots, which makes the selected-shot controls appear in a place where they compete with the splits.
- Scoring activity logs show placement and scoring are technically wired, but the UI does not clearly explain that a score is tied to a selected shot.
- Overlay, merge, layout, threshold, and scoring settings still require explicit apply buttons, which is not consistent with a local tool where changes can apply immediately.
- File imports log processing, but the page lacks a persistent visible processing/status bar while analysis is running.

## Goals

- Move Project to the top of the left rail and remove the duplicated Edit mode.
- Limit shot edit controls to the Timing workspace and make scoring controls explain selected-shot scoring explicitly.
- Make the waveform controls sit at the top of the waveform box.
- Remove the floating video status text that obscures split/overlay content.
- Add a visible processing/status bar for video import and API work.
- Shrink overlay color controls so they behave like compact tool settings.
- Auto-apply settings changes for threshold, scoring, overlay, merge, and layout.
- Add file-browser buttons for path fields where the browser can ask the local server to open a native chooser.
- Make `uv run splitshot` use the configured Python version without requiring `--python 3.12`.

## UI Plan

- Reorder the rail to Project, Review, Timing, Score, Overlay, Merge, Layout, Export.
- Remove the Edit pane because waveform editing is already always present in the main review/timing workspace.
- Move selected-shot nudge/delete controls into the Timing pane only.
- Keep scoring focused on per-shot score assignment and placement, not timing edits.
- Put the waveform canvas at the top of the waveform box, with controls below it.
- Hide the old video-status badge entirely.
- Add a thin status/progress bar below the metrics strip that appears during file imports and API calls.
- Tighten style-card grids, labels, and color input dimensions.
- Add compact picker buttons beside project path and export path inputs.

## Functional Plan

- Add browser API endpoints for local file/folder chooser actions.
- Add guarded frontend helpers that call chooser endpoints and populate path inputs.
- Add a debounce helper for automatic settings saves.
- Make overlay, layout, merge, threshold, scoring enabled, preset, penalties, and selected score changes save automatically.
- Keep export and project save/open/delete as explicit button actions because those are destructive or file-producing operations.
- Add logging for auto-apply, chooser requests, import start/finish, and processing state.
- Set the project Python requirement in `.python-version` so `uv run splitshot` resolves Python 3.12 from repo config.

## QA Plan

- Static tests verify Project-first rail order, Edit removal, no floating video-status copy, compact color controls, status bar presence, and auto-apply handlers.
- Browser control tests verify chooser endpoints return mocked paths and directory/file selection intent.
- Existing browser control tests continue covering file imports, scoring, overlay, sync, and display names.
- Run JavaScript syntax check, targeted browser tests, full test suite, runtime check, and review generated logs.

## Completion Status

- Project is now the first rail item.
- Edit mode was removed because waveform/timing own all editing behavior.
- Selected-shot nudge/delete controls now live only in Timing.
- Scoring now states that score letters attach to the selected shot, and video score placement only appears in Score mode.
- Waveform canvas now sits at the top of the waveform box with the control row below it.
- The old floating `No video open` / summary badge was removed.
- Import/API work now shows a processing/status bar.
- Overlay color controls were reduced to compact tool controls.
- Threshold, scoring, overlay, merge, and layout changes auto-apply.
- Project/export path fields have Browse buttons backed by local path chooser endpoints.
- README now documents `uv run splitshot` as the launch command, relying on `.python-version`.
