# Feature Plan

## Goal

Build a local-first Python desktop application that reproduces the workflow and user-facing capabilities described in `Directions.md` without cloud, auth, billing, or server dependencies.

## Product Flows

### Single Video

1. Create or open a project.
2. Load a primary video from disk.
3. Probe metadata and extract analysis audio.
4. Auto-detect timer beep and shot events.
5. Review and edit detections on the waveform.
6. Inspect split times, draw time, and shot count.
7. Configure overlays and scoring.
8. Preview the result.
9. Export a local MP4.
10. Save and reload the project without losing edits.

### Dual Video

1. Add a secondary video.
2. Probe metadata and detect beep in both videos.
3. Compute sync offset in milliseconds.
4. Preview side-by-side, above-below, or PiP.
5. Fine-tune offset and swap primary/secondary roles.
6. Export merged video with overlays and scoring.

## Feature Areas

### Media Ingest

- Support local `mp4`, `mov`, `avi`, `wmv`, `webm`, and other FFmpeg-readable formats
- Probe width, height, fps, duration, audio presence, and rotation
- Generate thumbnails and cached waveform data

### Analysis

- Deterministic baseline audio detector for timer beep and shot transients
- Adjustable sensitivity threshold
- Millisecond-based storage for all detections
- Split time and draw time computation

### Timeline Editing

- Click empty waveform to add shot
- Drag shot markers to move them
- Right-click or delete to remove a shot
- Shift-click beep marker to move it
- Double-click to seek
- Zoom, pan, playhead scrubbing, and keyboard nudging

### Merge

- Add/remove secondary video
- Auto-sync by beep timing
- Manual offset nudging in `1 ms` and `10 ms`
- Layouts: side-by-side, above-below, PiP
- PiP sizes: `25%`, `35%`, `50%`
- Swap primary and secondary

### Overlays

- Positions: none, top, bottom, left, right
- Timer badge
- Draw-time badge
- Shot split badges
- Current-shot highlight badge
- Hit-factor badge
- Badge style controls for color, text color, opacity, and size

### Scoring

- Enable or disable scoring mode
- Assign `A`, `C`, `D`, `M`, `NS`, `MU`, `M+NS`
- Place score letter on the preview
- Animate score mark fade/scale during preview and export
- Penalties and editable point map
- Hit factor calculation

### Export

- H.264 MP4 export
- Quality presets: high, medium, low
- Aspect ratios: original, `16:9`, `9:16`, `1:1`, `4:5`
- Draggable crop center
- Export overlays, scoring, and merged layouts
- Re-export saved projects

### Persistence

- New, save, save as, load, delete project
- Portable folder-based project bundle
- Unsaved changes warning
- Save full analysis, scoring, overlay, merge, and export state

### Preferences

- Default detection threshold
- Default overlay position
- Default merge layout
- Default PiP size
- Default export quality
- Badge size defaults
- Restore defaults

## Architecture Decisions

- `PySide6` for desktop UI and playback shell
- `numpy` plus FFmpeg-extracted PCM WAV for deterministic detection
- Custom waveform widget with `QPainter` to avoid extra rendering complexity
- FFmpeg wrappers for media probe, waveform extraction, thumbnails, and export
- Python compositor for export overlays to keep business logic in Python instead of brittle filter strings
- Folder-based `.ssproj` project bundles with JSON metadata and optional cached artifacts

## Delivery Order

1. Core models, settings, and FFmpeg integration
2. Single-video analysis and timeline editing
3. Project persistence
4. Merge and sync
5. Overlay and scoring preview
6. Export engine
7. Preferences and polish
8. Feature-focused tests and parity audit
