# Track 05: Waveform And Timeline Enhancements

## Goal

Enhance the waveform to support multi-angle editing and visual analysis.

## Multi-Track Waveform

### Requirements

- one waveform track per video/angle
- tracks are stacked vertically
- each track has:
  - file name label
  - camera job badge
  - mute/solo buttons
  - volume fader
- all tracks share a synchronized playhead
- zoom and pan affect all tracks together
- amplitude scaling per track

### Colors

- primary angle: blue
- follow angle: green
- static angle: yellow
- detail angle: purple
- selected track: accent highlight

## Color-Coded Segments

### Requirements

- auto-detect segments:
  - Moving (shooter in motion)
  - Static (shooter stationary)
  - Long Move (extended movement)
- show as colored bands behind the waveform
- bands are semi-transparent
- legend shows color meanings
- hover shows segment type and duration

### Detection

- use motion analysis or audio energy
- fallback to manual assignment
- segments are output-profile-local

## Auto-Cut Visualization

### Requirements

- show suggested cut points as vertical lines
- lines are dashed and colored by confidence
- hover shows cut reason (motion, audio, manual)
- click to accept/reject
- accepted cuts become solid lines
- rejected cuts disappear

## Playhead Sync

### Requirements

- playhead moves smoothly across all tracks
- click anywhere to seek
- drag to scrub
- keyboard arrows nudge by frame
- sync nudge controls for multi-angle alignment

## Acceptance

- multi-track waveform renders at 30fps minimum
- color-coded segments are visually distinct
- auto-cut lines are accurate and actionable
- playhead sync is smooth
- all tracks stay synchronized during zoom and pan
