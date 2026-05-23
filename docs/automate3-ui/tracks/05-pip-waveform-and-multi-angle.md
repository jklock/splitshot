> **Note:** Track status is partial. See `../todo.md` for live checklist.


# Track 05: PiP, Waveform, And Multi-Angle

## Goal

Make visual sync and multi-angle editing smooth enough for real work.

## PiP Smoothness Contract

- small drift uses bounded playback-rate correction
- large drift triggers one hard seek
- hard seek allowed on attach, manual scrub, play/pause boundary, explicit sync, large drift, source reset
- drag suspends heavy reseek and overlay recompute
- drag is RAF-driven locally
- route commit happens on pointerup or debounced settle.

## Waveform Requirements

- multi-track waveform
- one track per angle
- synchronized playhead
- camera-job colors
- mute/solo/gain controls
- color-coded segments
- auto-cut markers.

## Multi-Angle Requirements

- line up angles
- smart angle switching
- camera jobs
- audio balance
- override smart cuts
- preview of resulting cuts.

## Proof

- no per-frame route churn
- no steady playback reseek churn
- loaded multi-angle screenshot
- interaction test for drag commit
- performance audit updated.
