# Browser Static Frontend

This directory contains the browser shell that talks to the local SplitShot API.

## Files

- [index.html](index.html) defines the page layout and all control ids.
- [app.js](app.js) owns the frontend state machine, rendering, event handlers, and API calls.
- [styles.css](styles.css) defines the cockpit layout and control styling.
- [logo.png](logo.png) is the brand image used in the left rail.

## HTML Structure

`index.html` is organized into these major regions:

- the left tool rail with the Project, Splits, Score, Overlay, Merge, Review, and Export page buttons
- the status strip with draw, raw, shot count, and average split metrics
- the review grid with the video stage, waveform panel, timing workbench, and inspector
- the inspector tool panes for page-specific controls

Important control ids and data attributes include:

- `primary-file-input`, `merge-media-input`, `project-path`, and `export-path`
- `toggle-layout-lock-video`, `toggle-layout-lock-waveform`, and `toggle-layout-lock-inspector`
- `resize-rail`, `resize-waveform`, and `resize-sidebar`
- `data-tool`, `data-tool-pane`, `data-waveform-mode`, `data-sync`, and `data-nudge`

## JavaScript State Flow

`app.js` keeps the browser state in a small set of top-level variables:

- the last server state payload
- the selected shot id
- the active tool pane
- waveform zoom and offset values
- the current layout lock state and resize measurements
- local draft state for export and timing edits

The main rendering loop:

1. Fetches `/api/state` or posts to an API route.
2. Applies the response to local state.
3. Re-renders the video stage, waveform, split lists, timing tables, and inspector fields.
4. Logs the user action to `/api/activity`.

## Frontend Behavior

- Layout sizing uses CSS custom properties such as `--app-height`, `--rail-width`, `--inspector-width`, and `--waveform-height`.
- Waveform zoom and offset persist in `localStorage`.
- The active tool pane persists in `localStorage`.
- Browser controls are normalized for WebKit/Safari so the native inputs stay usable inside the cockpit layout.

## Editing Notes

- The frontend depends on the backend routes in `browser/server.py`; update both sides when adding or renaming an action.
- After changing static assets, refresh the running browser page before validating the behavior.