# UX And Automation Gap Analysis

## Current State

The app is functionally broad, but the current interaction model still exposes the implementation more than the product flow. The screenshot from the current build confirms this: the user is presented with a mostly blank interface, multiple large generic action buttons, and manual analysis steps before the workflow feels useful.

## Gaps

### Entry Experience

- Missing dedicated upload-first empty state
- Missing drag-and-drop guidance
- Missing first-run copy that explains what happens automatically

### Automation

- Primary video load and analysis are separate user actions
- Secondary video load and sync analysis are separate user actions
- Automatic completion feedback is weak

### Visual Hierarchy

- Preview, waveform, and split review are not visually separated into clear product panels
- There are no stat cards or top-level cues for “what matters now”
- The current default Qt styling reads as tooling rather than product
- The loaded-video state does not resemble the Shot Streamer review surface with its left rail, top metrics, waveform card, and split cards

### Progressive Disclosure

- Too many equal-weight controls are visible at once
- The app does not clearly lead the user from upload to review to export
- Re-run analysis and advanced controls are not visually distinguished from first-run actions

### Merge Review

- Secondary waveform behavior is implemented in the model but not surfaced as a dedicated view-first panel
- Sync status is technically present but not presented as a user-friendly review state

## Closure Plan

1. Introduce upload-first ingest methods in the controller.
2. Replace manual primary/secondary analysis entry points with auto-ingest actions.
3. Build a guided empty state and richer preview shell.
4. Add stat cards and clearer panel structure.
5. Replace the default shell with workflow navigation and a loaded-video review layout closer to Shot Streamer.
6. Add a dedicated secondary waveform panel in merge mode.
7. Refine project, merge, overlay, scoring, layout, and export controls into contextual grouped panels.
8. Add tests for auto-ingest and the refreshed UX flow.
9. Audit the refreshed build against both `Directions.md` and Shot Streamer.
