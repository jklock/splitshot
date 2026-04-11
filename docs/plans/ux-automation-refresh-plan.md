# UX And Automation Refresh Plan

## Goal

Refit SplitShot around the upload-first, auto-processing workflow and user-friendly control model shown in Shot Streamer while keeping the local-first architecture and existing feature coverage from `Directions.md`.

## Baseline Review

### Directions.md Requirements Relevant To This Pass

- Uploading a video should start the user flow immediately
- Shot and beep detection are automatic before manual correction
- The waveform editor remains core, but it should feel like a refinement step instead of the starting point
- Merge, scoring, overlays, and export should remain available without exposing unnecessary complexity up front

### Shot Streamer UX Patterns To Mirror

- Clear empty-state upload entry point
- Automatic processing after upload
- Strong visual hierarchy around preview, timer, waveform, and key actions
- Helpful defaults and progressive disclosure
- Contextual controls instead of a wall of generic buttons
- A workflow that makes the “next step” obvious
- A loaded-video review state centered on:
  - left navigation for major workflows
  - top summary cards
  - a large video canvas
  - an interactive waveform editor card with editing instructions
  - a split-times card grid that reads like review output rather than raw table data

## Product Changes For This Pass

### Upload-First Flow

1. User sees a guided upload surface when no primary video is loaded.
2. User uploads or drops a video.
3. App automatically probes media and runs primary analysis.
4. UI updates to a review state with stats, waveform, split table, and playback ready.
5. User optionally adds a second angle, which also auto-analyzes and syncs.

### Control Simplification

- Replace the current “load” plus separate “analyze” pattern with “upload and analyze”
- Keep manual “re-run analysis” actions in the analysis area for advanced correction
- Group project actions, analysis controls, and output controls into clearer sections
- Disable or hide irrelevant controls until prerequisites exist

### Visual Layout Refresh

- Add a branded empty state for the first-run experience
- Introduce stat cards for shots, draw time, stage time, average split, and sync state
- Turn preview, waveform, split review, and section settings into distinct dark product panels with headers and helper copy
- Replace the existing raw tab-heavy shell with a workflow shell closer to the Shot Streamer reference:
  - left rail for workflow sections
  - center review surface for loaded-video work
  - contextual controls only for the active section
- Improve the Qt stylesheet so the app no longer looks like raw default widgets

### Merge Review UX

- Show a separate secondary waveform panel in merge mode
- Make sync adjustment controls more obvious and grouped
- Reflect merge status in summary cards instead of only raw offset text

### Automatic Feedback

- Show progress dialogs or processing messages during automatic ingest
- Push status text to the UI so the user knows what happened after upload
- Use automatic selection and sensible focus changes after analysis completes

## Implementation Areas

### Controller

- Add ingest helpers that load and auto-analyze primary and secondary videos
- Add lightweight status messages for UI feedback

### UI

- Replace the current plain preview empty state with a drag-and-drop upload panel
- Refresh navigation into workflow sections and smarter defaults
- Add stat cards, an interactive waveform card, and split cards for loaded projects
- Preserve manual editing once the automatic steps finish

### Tests

- Verify upload-triggered ingest performs automatic analysis
- Verify the refreshed empty state and preview selection flow
- Keep tests feature-oriented and avoid style-only assertions

## Done Criteria

- The first meaningful user action is upload, not manual setup
- Primary upload automatically produces waveform, beep, shots, and stats
- Secondary upload automatically produces sync offset and merge-ready state
- The default screen is visually structured and user-friendly instead of utility-first
- The loaded-video screen clearly resembles the Shot Streamer interaction model without copying cloud-only SaaS features
- Existing feature coverage remains intact
