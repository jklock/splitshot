# Browser Waterfall Workflow Repair Plan

## Goal

Repair the browser-first workflow so it behaves like a local video review tool instead of a collection of loosely connected panels. The left rail is a waterfall: Project, Splits, Score, Overlay, Merge, Layout, Review, Export.

## Direction Sources Reviewed

- `Directions.md`: local Shot Streamer parity, local project files, automatic analysis, waveform editing, dual-video merge, overlays, scoring, export.
- Latest browser logs: button/activity logging shows API calls succeeded, but preview behavior and page state were not always observable or correct.
- User screenshots and notes: secondary video was invisible, status bar persisted visually, waveform lacked scale/zoom, review/splits/layout responsibilities were confused, and several controls were misnamed or misplaced.

## Required UX Changes

- Project pane: rename secondary action to `Add Second Video`; make `Delete Project` a full-width red destructive action.
- Left rail: rename Timing to Splits and move Review near the end above Export.
- Status bar: display only during primary/secondary analysis or MP4 export.
- Secondary video: show WYSIWYG merge preview in the same video stage when a second video is added and merge is enabled.
- Waveform: add visible time scale, zoom controls, amplitude controls, and millisecond-precision labeling.
- Expanded modes: waveform/splits expansion must collapse when changing pages; unlock controls only appear with expanded waveform controls.
- Splits: remove split-card clutter from Review and make Splits the timing-edit page.
- Scoring: each shot row must show shot time and assigned score; overlay split badges must include score text inside the shot badge instead of floating score letters.
- Overlay/Layout: expose shot count, quadrant, direction, custom X/Y, font, text style, bubble size, colors, and artifact toggles with auto-apply behavior.
- Review: become a preview-artifact/custom text box page, not a splits page.
- Export: keep FFmpeg export path and log visible, ensure local MP4 output is actually produced in tests.

## Implementation Plan

1. Update data model and persistence for overlay placement, shot display count, custom position, font styling, artifact toggles, and custom review box text.
2. Update browser state/API/controller so overlay payloads round-trip these new settings.
3. Refactor browser markup to match the waterfall page model and remove duplicate controls.
4. Patch JS rendering so every visible control has a state mutation, preview mutation, export mutation, or gets removed.
5. Patch WYSIWYG secondary preview with synchronized primary/secondary playback and merge-layout CSS.
6. Patch waveform renderer to use visible-window math, scale labels, zoom controls, and matching hit-testing.
7. Patch overlay preview/export renderer to use the same settings and embed shot scores inside split badges.
8. Add feature-level tests for browser state, overlay/export output, secondary preview wiring, static button wiring, and workflow constraints.
9. Generate a Stage1 all-options MP4 and a preview frame for inspection.
10. Commit the branch and merge back into `main`.

