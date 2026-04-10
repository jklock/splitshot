# UI Plan

## Main Window

### Primary Layout

- Header toolbar for project, analysis, merge, and export actions
- Center preview area with playback controls
- Right sidebar with tabbed controls
- Bottom waveform editor across full width
- Lower table for split times and scores

### Panels

#### Project

- New, open, save, save as, delete
- Primary and secondary media selectors
- Recent file paths and metadata summary

#### Analysis

- Analyze primary
- Analyze secondary
- Detection threshold slider
- Read-only stats: beep time, total shots, draw time, total time

#### Merge

- Enable merge toggle
- Add/remove secondary video
- Layout selector
- PiP size selector
- Offset controls for `-10`, `-1`, `+1`, `+10` ms
- Swap videos

#### Overlay

- Overlay position selector
- Badge size selector
- Style editors for timer, shot, current-shot, and hit-factor badges

#### Scoring

- Enable scoring
- Point-map editor
- Penalties field
- Letter assignment controls
- Current shot placement instructions

#### Export

- Output path
- Quality selector
- Aspect ratio selector
- Crop center controls
- Export action with progress feedback

## Preview

- Single-video mode uses a single player surface with overlay layer
- Merge mode uses a layout container with synchronized primary and secondary players
- Overlay layer reads app state and the current playback position
- Clicking preview in scoring mode stores normalized letter placement for selected shot

## Waveform Editor

- Full-width custom widget
- Cached waveform envelope for fast paint
- Beep marker in a distinct color
- Shot markers with selection highlighting
- Visible zoom window and panning offset
- Playhead follows playback and seeks on user interaction

## Split Table

- Columns: shot, absolute time, split, score, source, confidence
- Row selection syncs with waveform and scoring controls
- Editable score column via combo box

## Dialogs

- Preferences dialog
- Export progress dialog
- Unsaved changes confirmation
- Delete project confirmation

## Usability Rules

- All timing displayed in milliseconds with second-friendly formatting
- Disable actions that require missing prerequisites
- Long-running analysis and export run in background threads
- Keep text explicit and task-oriented; no hidden feature modes
