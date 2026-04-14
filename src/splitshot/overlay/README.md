# Overlay

The overlay package draws the review badges that appear on top of the video preview and exported frames.

## Files

- [render.py](render.py) defines `Badge` and `OverlayRenderer`.

## Rendering Responsibilities

`OverlayRenderer` builds and paints these visual elements:

- the elapsed timer badge
- the draw-time badge before the first shot
- the current shot badge trail
- the final score or hit-factor badge when scoring is enabled
- the custom review box

## Dependencies

- `draw_time_ms` and `current_shot_index` come from the timeline and scoring layers.
- `calculate_scoring_summary` provides the final score label/value.
- `format_time_ms` formats timer and split values for display.

## Notes

- The badge layout honors `OverlaySettings` fields such as position, spacing, margin, font family, badge size, and quadrant.
- Custom boxes can use their own position, dimensions, colors, opacity, and text.
- The renderer paints directly into a `QPainter`, which makes it usable both in the browser preview path and in export.

**Last updated:** 2026-04-13
**Referenced files last updated:** 2026-04-13
