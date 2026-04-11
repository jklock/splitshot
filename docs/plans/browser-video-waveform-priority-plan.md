# Browser Video Waveform Priority Plan

## Goal

Redesign the browser cockpit around the actual usage priority:

1. Video review window.
2. Waveform and timeline editing.
3. Everything else in the right sidebar.

## UI Requirements

- Remove the command strip/top row.
- Remove the empty-state row and horizontal metric row.
- Keep the video window as the dominant center workspace.
- Keep the waveform directly below the video as the second-priority control.
- Move open stage video, second angle, refresh, status, metrics, selected-shot controls, split cards, project controls, scoring, overlay, merge, layout, and export into the right sidebar.
- Keep the left rail as navigation only.
- Keep the logo constrained to the rail brand cell.
- Prevent content from escaping panels or overlapping.
- Preserve square, contiguous tool styling.

## Functional Requirements

- Primary and secondary local file pickers must continue to open native file dialogs.
- Refresh, new project, threshold application, timing edits, shot nudges/deletes, scoring, overlay, merge, layout, project persistence, and export must remain wired.
- State updates must still render the same metrics and timing data.
- The page must stay fixed-height on desktop, with internal scrolling only in the right sidebar or split lists as needed.

## Test Plan

- Static UI tests verify there is no command strip, no empty top row, and no horizontal metric strip.
- Static UI tests verify the cockpit grid is a center review workspace plus right inspector.
- Static UI tests verify video appears before waveform in the central review stack.
- Existing browser/API tests verify file import and state actions remain functional.
- Full test suite verifies analysis, scoring, export, desktop, and packaging behavior did not regress.
