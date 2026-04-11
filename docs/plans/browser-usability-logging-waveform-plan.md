# Browser Usability Logging Waveform Plan

## Log Review

No existing activity log files were present before this pass. The repository had no `logs/` files and no browser run log to inspect, so the first implementation step is to add always-on run logging.

## Goal

Make the browser app usable as a focused local review tool:

1. Center workspace: video and waveform.
2. Top strip: only filename and compact metrics.
3. Right sidebar: only the active tool content.
4. Left rail: readable navigation with constrained logo.
5. All user and server activity logged to console and a per-run file.

## UI Requirements

- Remove always-visible Open Stage Video, Add Second Angle, and Refresh buttons from the right sidebar.
- Remove the bottom `New` button from the left rail.
- Make left rail text brighter, bolder, and visually consistent with the rest of the app.
- Make the logo fill the left rail brand cell without escaping its container.
- Add a thin top metrics strip with current filename, draw, raw, shot count, and average split.
- Keep the top strip free of command buttons.
- Hide selected-shot controls unless the active tool actually needs them.
- Audit all right-sidebar panes for consistency and remove global clutter.

## Waveform Requirements

- The waveform panel has an expand/collapse control.
- Expanded waveform mode hides the right sidebar and gives the waveform most of the workspace.
- The waveform draws shot numbers and times directly on the canvas.
- Selecting a shot highlights its waveform region.
- Pointer drag moves the selected shot.
- Keyboard editing supports left/right nudge and delete.
- Add-shot and move-beep actions are explicit modes, not accidental default clicks.
- A shot list under the waveform provides direct selection by shot/time.

## Timing Requirements

- Timing has an expand/collapse control.
- Expanded timing mode uses the center workspace and hides the right sidebar.
- Timing rows select shots and expose the same selected-shot keyboard/nudge behavior.

## Logging Requirements

- Every browser run creates a new log file in `logs/`.
- Server events log to terminal and file.
- Browser events log to browser console and POST to the server log.
- API route starts, successes, failures, media requests, file imports, tool switches, waveform actions, timing actions, scoring, overlay, merge, layout, and export all emit activity records.

## Test Plan

- Add server tests for per-run activity log creation and API logging.
- Add static UI tests for removal of duplicate command buttons and the bottom rail New button.
- Add static UI tests for the top metrics strip, contextual selected-shot controls, waveform expansion, timing expansion, and keyboard/pointer handlers.
- Keep existing browser API tests for import, edit, score, merge, overlay, and export behavior.
- Run the full suite after implementation.
