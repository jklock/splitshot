# Timing Exposure and UI Parity Gap Analysis

## Gap 1: Cumulative Beep-To-Shot Timing Is Not Explicit

Current output includes draw, raw, absolute shots, and shot-to-shot splits. It does not explicitly expose cumulative beep-to-shot timing for every shot.

Closure:

- Add `timing_segments` and CSV `beep_to_shot_*` columns.

## Gap 2: Draw Is Not Represented As `split_1`

Shot timers treat draw as the first segment from beep to first shot. Current CSV has `draw_ms`, but split columns start at `split_2`.

Closure:

- Add `split_1_ms` and `split_1_s` as draw while keeping `draw_*`.

## Gap 3: Browser And Desktop Build Split Cards Separately

The browser builds cards from JSON rows and the desktop builds cards from timeline rows. They can drift in labels, values, and metadata.

Closure:

- Add a shared presentation builder and use it in both UIs.

## Gap 4: Tests Need To Lock The Shared Contract

Current tests cover each surface, but not that they expose the same timing contract.

Closure:

- Add tests for `build_stage_presentation`, browser state timing segments, desktop split-card parity, and CSV timing columns.
