# Track 03: Single Video UI

## Goal

Make the stage editor expose the new automation output model as a first-class UI.

## Existing UI To Preserve

- timing
- scoring
- markers
- overlay
- review
- metrics
- ShotML

## Required Additions

- output-profile manager
- profile list
- create / duplicate / rename / delete
- retained-review source selector
- `Run Window` editor
- `Metric Captions` editor
- `Frame Profiles` editor
- `Lead-In Card` editor
- `Brand Mark` editor
- `Subject Track Crop` hooks
- render-plan summary
- render-result state

## Workspace-Aware Requirements

When opened from `Multi Video`, Single Video must also show:

- inherited/defaulted status
- stage-local override visibility
- clear return-to-workspace affordance

## Acceptance

- stage editing remains deep and focused
- multiple outputs from one truth record are visible and usable
