# Presentation

The presentation package builds the stage summary objects consumed by the browser dashboard and the desktop UI.

## Files

- [stage.py](stage.py) defines the formatting helpers, stage metrics, timing segments, and `build_stage_presentation`.

## Data Model

- `StageMetrics` stores draw time, raw time, stage time, shot count, average split, beep time, and final shot time.
- `TimingSegment` stores the per-shot labels and the formatted card data used in the browser UI.
- `StagePresentation` groups the metrics and timing segments together.

## Output Behavior

- `build_stage_presentation` sorts the shots, derives draw and split values, and labels each segment as Draw or Shot N.
- `format_seconds_short` and `format_seconds_precise` format values for compact UI display.
- The browser state exposes the same data as `metrics` and `timing_segments`.

## Consumers

- `browser.state.browser_state` serializes the presentation data into the JSON API response.
- `ui.main_window.MainWindow` uses the same presentation data to populate the desktop dashboard.

**Last updated:** 2026-04-13
**Referenced files last updated:** 2026-04-13
