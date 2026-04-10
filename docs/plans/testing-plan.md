# Testing Plan

## Principle

Tests verify user-facing features and domain behavior. They do not assert styling details, widget geometry trivia, or implementation-specific counts that are not part of the product behavior.

## Automated Coverage

### Analysis

- Detect a synthetic timer beep near the expected timestamp
- Detect synthetic shot transients with stable ordering and spacing
- Respect threshold changes
- Compute draw time and splits correctly

### Merge

- Compute sync offset from two analyzed videos
- Swap primary and secondary merge roles without losing timing
- Produce correct output canvas sizes for side-by-side, above-below, and PiP

### Scoring

- Persist per-shot score letters and placement
- Compute hit factor with penalties and editable point map
- Identify current shot at playback time

### Persistence

- Save and load a project bundle round-trip
- Preserve analysis, merge, overlay, scoring, and export settings
- Detect unsaved changes when state differs from the saved snapshot

### Export

- Export a short synthetic MP4 file successfully
- Render overlays and score annotations into the output frames
- Apply non-original aspect ratio crop dimensions

### UI

- Waveform interactions add, move, and delete shot markers
- Playback position changes update selection and playhead
- Score placement on preview stores normalized coordinates

## Manual Validation

- Open real-world video assets with audio
- Compare preview timing with export timing
- Validate merge sync adjustments at `1 ms` and `10 ms`
- Validate crop preview for all aspect ratio options
- Validate save/reload/re-export flow

## Acceptance Matrix

The acceptance matrix mirrors the fifteen parity checks listed in `Directions.md`. Every item must be backed by implemented code and at least one automated or explicit manual verification path.
