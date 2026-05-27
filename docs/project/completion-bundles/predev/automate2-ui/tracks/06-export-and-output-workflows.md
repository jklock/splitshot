# Track 06: Export And Output Workflows

## Goal

Make export and output workflows clear, previewable, and trackable.

## Single Stage Export

### Requirements

- output profile selector
- preview button (shows what the output will look like)
- render button
- progress indicator
- completion notification
- open output folder button

## Batch Export

### Requirements

- select stages to export
- select output recipe
- preview one stage to verify settings
- start batch button
- queue panel showing:
  - stage name
  - status (queued, rendering, done, failed)
  - progress bar
  - estimated time
  - cancel button
- completion summary:
  - total rendered
  - total failed
  - open output folder button

## Match Recap Export

### Requirements

- stage inclusion/exclusion
- stage ordering
- result card configuration
- transition style
- preview before render
- render button
- progress indicator

## Stage Composite Export

### Requirements

- clip list and ordering
- camera job per clip
- audio balance
- cut plan
- preview before render
- render button
- progress indicator

## Output Preview

### Requirements

Every output setting must have a preview:

- Trim Dead Time: show trim boundaries
- Shot Data on Screen: show overlay on video
- Video Shape: show crop frame
- Opening Title: show title card
- Your Logo: show watermark
- Keep Shooter in Frame: show crop rectangle
- Smart Angle Switching: play auto-directed sequence

## Acceptance

- every output setting is previewable
- batch export shows clear progress
- failed exports show helpful errors
- completion is celebrated
- output files are easy to find
