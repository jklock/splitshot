# Timing Exposure and UI Parity Plan

## Inputs

- Stage actuals are benchmark data only.
- Production detection must remain generic and must not hard-code stage names or stage times.
- Raw time is the score-table benchmark metric.
- Users need all timing data from timer beep through final shot, split-by-split.
- Browser mode is primary, desktop mode is secondary, but both should present and operate on the same data.

## Goals

1. Expose a full timing timeline:
   - timer beep time
   - draw segment
   - each shot-to-shot split
   - cumulative beep-to-shot time for every shot
   - final raw time
2. Use the same presentation data in browser and desktop UI.
3. Add CSV columns for `split_1` as draw and `beep_to_shot_*` cumulative timing.
4. Add tests that prove browser and desktop consume the same split/timing contract.
5. Keep detector logic generic.

## Shared Data Contract

Add a presentation module that builds:

- `metrics`: draw, raw, shot count, average split, beep, final shot.
- `timing_segments`: one row per shot:
  - shot number
  - label (`Draw`, `Shot 2`, ...)
  - shot id
  - segment duration
  - cumulative beep-to-shot duration
  - absolute video timestamp
  - confidence
  - score/source metadata

Consumers:

- Browser API state.
- Browser split cards/timing details.
- Desktop split cards.
- Benchmark CSV.

## UI Parity Target

Browser and desktop should use the same wording and behavior for:

- Stat card labels: Draw Time, Raw Time, Total Shots, Avg Split.
- Timing card titles: Draw, Shot 2, Shot 3, etc.
- Timing card value: current segment duration.
- Timing card metadata: cumulative beep-to-shot time and absolute video timestamp.
- Shot selection, shot nudge, delete, scoring assignment, overlay, merge, layout, and export controls.

## Acceptance

- `artifacts/stage_suite_analysis.csv` includes `split_1_*` and `beep_to_shot_*`.
- Browser state includes `timing_segments`.
- Desktop split cards use the shared timing segments.
- Tests pass and cover shared timing parity.
