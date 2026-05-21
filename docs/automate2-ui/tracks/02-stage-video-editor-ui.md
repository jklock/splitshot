# Track 02: Stage Video Editor UI

## Goal

Make the stage editor expose the new automation output model as a first-class UI, with all multi-angle and waveform enhancements.

## Existing UI To Preserve

- timing
- scoring
- markers
- overlay
- review
- metrics
- ShotML
- waveform
- PiP

## Required Additions

### Output Profile Manager

- profile list with names and types
- create / duplicate / rename / delete
- active profile selection
- retained-review source selector

### Output Hook Editors (with Preview)

Each editor must show a live preview on the video:

- **Trim Dead Time** — start/end handles on waveform, padding inputs, preview updates
- **Shot Data on Screen** — preset selector, visibility toggles, preview shows data
- **Video Shape** — aspect ratio selector, preview shows crop frame
- **Opening Title** — text fields, style selector, preview shows title card
- **Your Logo** — image upload, position, opacity, preview shows watermark
- **Keep Shooter in Frame** — crop rectangle on video, track/reset buttons

### Multi-Angle Features

- **Smart Angle Switching** — suggestion list, accept/reject/move, preview plays cuts
- **Line Up Angles** — sync button, offset display, nudge controls, layout selector
- **Camera Jobs** — role dropdown per angle (Primary, Follow, Static, Detail)
- **Audio Balance** — per-angle mute, gain slider, primary audio selector
- **Override Smart Cuts** — cut list with timecodes, accept/reject/move, preview updates

### Waveform Enhancements

- **Multi-Track Waveform** — one track per angle, color-coded, synchronized playhead
- **Color-Coded Segments** — auto-labeled bands (Moving, Static, Long Move)
- **Auto-Cut Visualization** — vertical lines at suggested cut points

### Workspace-Aware Requirements

When opened from `Match Video Edit`, Stage Video Edit must also show:

- inherited/defaulted status
- stage-local override visibility
- clear return-to-workspace affordance
- "Apply settings to all stages" button (if this is Stage 1)

## Acceptance

- stage editing remains deep and focused
- multiple outputs from one truth record are visible and usable
- every output setting has a live preview
- multi-angle features are usable without expert knowledge
- waveform enhancements render smoothly
