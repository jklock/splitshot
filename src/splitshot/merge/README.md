# Merge

The merge package computes the canvas geometry used for dual-angle previews and export.

## Files

- [layouts.py](layouts.py) defines `Rect`, `MergeCanvas`, and `calculate_merge_canvas`.

## Layout Modes

- `MergeLayout.SIDE_BY_SIDE` scales both sources to the same height and places them horizontally.
- `MergeLayout.ABOVE_BELOW` scales both sources to the same width and stacks them vertically.
- `MergeLayout.PIP` keeps the primary frame full size and places the secondary source as an inset.

## Inputs and Outputs

`calculate_merge_canvas` takes:

- the primary and optional secondary `VideoAsset`
- the selected `MergeLayout`
- the PiP size as a `PipSize`, integer percent, or float percent
- optional PiP coordinates

It returns a `MergeCanvas` with the output width and height plus the rectangle for each source.

## Implementation Notes

- PiP placement clamps coordinates to the unit interval and keeps the inset away from the frame edges.
- The same geometry helper is used by the browser preview and the export pipeline.

**Last updated:** 2026-04-13
**Referenced files last updated:** 2026-04-13
