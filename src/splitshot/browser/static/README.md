# Browser Static Assets

This directory contains the browser-first SplitShot shell that talks to the local API.

## Files

- [index.html](index.html) defines the browser shell structure and the control ids used by tests and API wiring.
- [app.js](app.js) owns browser state, rendering, activity logging, auto-apply behavior, metrics export, and modal interactions.
- [styles.css](styles.css) defines the cockpit layout, status bar, modal styling, metrics cards, and text-box editors.
- [logo.png](logo.png) and [githublogo.png](githublogo.png) are the browser branding assets.

## Shell Structure

`index.html` is organized into these major regions:

- the left rail with Project, PiP, Score, Splits, Markers, Overlay, Review, Export, Settings, Metrics, and ShotML tools
- the persistent status bar that shows the selected video name or `No Video Selected`
- the review grid with the stage preview, waveform, timing workbench, and inspector
- inspector panes for project metadata, scoring, timing, ShotML, PiP, overlays, markers, review text boxes, export controls, settings, and metrics
- the color picker and export log modals used by overlay, markers, review, and export controls

Important ids and data attributes include:

- `primary-file-input`, `merge-media-input`, `project-path`, `export-path`, and `practiscore-file-input`
- `timing-table`, `timing-workbench-table`, `timing-event-list`, `score-option-grid`, and `scoring-shot-list`
- `review-text-box-list`, `popup-marker-list`, `markers-workbench`, `markers-workbench-list`, `markers-workbench-editor`, `settings-scope-status`, `metrics-summary-grid`, `metrics-trend-list`, and `metrics-score-summary`
- `show-export-log`, `export-log-modal`, `export-log-output`, and `export-log-error`
- `color-picker-modal`, `color-picker-hue`, `color-picker-saturation`, `color-picker-lightness`, and `color-picker-hex`
- `toggle-layout-lock-video`, `toggle-layout-lock-waveform`, `toggle-layout-lock-inspector`, `resize-rail`, `resize-waveform`, and `resize-sidebar`
- `data-tool`, `data-tool-pane`, `data-waveform-mode`, `data-sync`, `data-nudge`, `data-open-merge-media`, and popup/text-box data action attributes

## Browser State Flow

`app.js` keeps a compact set of top-level browser variables for:

- the latest server state payload
- the selected shot and active tool
- waveform zoom and offset state
- layout lock and resize state
- progress and activity polling state
- repeatable overlay text-box, marker, settings-summary, and color-picker state
- export path drafts and export log lines

The main loop is:

1. Fetch `/api/state` or post to an API route.
2. Apply the payload to browser state.
3. Re-render the preview, waveform, metrics, timing tables, and inspector controls.
4. Mirror user actions into `/api/activity`.
5. Poll `/api/activity/poll` so export progress and log output can update in real time.

## Shell Behavior

- Layout sizing uses CSS variables such as `--app-height`, `--rail-width`, `--inspector-width`, and `--waveform-height`.
- Waveform zoom, waveform offset, and active tool state persist in `localStorage`.
- Review and export overlays share the same repeatable text-box model, including imported summary boxes and manual notes.
- Shot-level score and penalty edits live in the Scoring pane; the Splits pane focuses on timing edits.
- Markers are separate from review text boxes and can be time-based, shot-linked, image-based, or motion-following, with a compact pane for browsing and a dedicated workbench for focused editing.
- Export progress uses the processing bar plus the live export log modal.
- Browser controls are normalized for WebKit and Safari-class browsers so native inputs remain usable in the cockpit layout.

## Editing Notes

- The browser shell depends directly on `browser/server.py` routes; update both sides when changing action names or payload contracts.
- After editing static assets, reload the running page before validating behavior so you are not testing a stale bundle.

**Last updated:** 2026-04-30
**Referenced files last updated:** 2026-04-30
