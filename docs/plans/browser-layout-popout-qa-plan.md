# Browser Layout Popout QA Plan

## Log Review

Reviewed the latest run logs before changes. Findings:

- Button and tool navigation activity is reaching `/api/activity`, but not every button is logged generically.
- Primary and secondary file imports are logged, but display paths show UUID-prefixed temp filenames.
- Waveform clicks log seek events, which means the current interaction still behaves like a compact waveform, not a focused popout editor.
- Media range requests and analysis completion are logged as expected.

## Goals

- Make the logo visually fill the left rail brand cell.
- Make the top metrics strip consistent with the grid below it.
- Prevent right sidebar horizontal movement and visual overlap.
- Preserve user-visible filenames instead of UUID temp names.
- Make waveform expansion a true main-workspace popout.
- Log every button click across the browser app.
- Add a QA audit that maps each browser button to its logged activity and app effect.

## UI Plan

- Enlarge the rail and logo cell and scale the logo within the clipped cell.
- Convert the top status strip into a fixed 5-column grid aligned to stable cells.
- Use a fixed right sidebar width with `min-width: 0`, no horizontal scrolling, and breakable path text.
- Remove compact-mode waveform button clutter when expanded and make expanded waveform replace the video area.
- Keep timing expansion as a workbench that also removes sidebar movement.

## Functional Plan

- Track original uploaded filenames server-side for each temp file.
- Expose display names in browser state without changing media paths.
- Update frontend `fileName` and details rendering to use display names.
- Add global capture-phase logging for every button click.
- Keep route-level server logging for all effects.

## QA Plan

- Static tests verify logo sizing, top strip grid, sidebar fixed width, no horizontal overflow, and true waveform popout CSS.
- Server tests verify uploaded display names do not expose UUID prefixes.
- Static tests verify global button logging exists.
- Add a browser button QA document listing each button, its behavior, and validation method.
- Run targeted browser tests, full suite, runtime check, and a smoke test against the browser server.

## Completion Status

- Implemented display-name preservation and user-facing filename rendering.
- Implemented fixed metric cell sizing, fixed inspector width, and horizontal overflow clamping.
- Implemented true waveform popout behavior that hides the video and inspector.
- Implemented global button/control logging and additional score-placement activity logs.
- Added the button QA audit and final validation audit.
- Passed targeted browser tests, full test suite, runtime check, JavaScript syntax check, and button activity smoke validation.
