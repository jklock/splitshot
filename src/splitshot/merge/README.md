# Merge

<!-- Documentation reviewed: 2026-08-11 -->

This package owns layout geometry for side-by-side, above-below, and picture-in-picture composition shown in the Compose pane.

## Purpose

Use it when the change affects added-media placement, merge canvas sizing, or export and preview geometry for secondary media.

## Read This First

- [layouts.py](layouts.py)

## Main Files

- [layouts.py](layouts.py): `Rect`, `MergeCanvas`, and `calculate_merge_canvas`

## Runtime Flow

1. Accept the primary and optional secondary assets plus layout settings.
2. Compute the output canvas size.
3. Return the source rectangles used by preview and export layers.

## Key Extension Points

- `calculate_merge_canvas`

## Related Tests

- [../../../tests/export/test_merge_export_contracts.py](../../../tests/export/test_merge_export_contracts.py)
- [../../../tests/scoring/test_scoring_and_merge.py](../../../tests/scoring/test_scoring_and_merge.py)

## Related Docs

- [../export/README.md](../export/README.md)
- [../../../docs/userfacing/panes/compose.md](../../../docs/userfacing/panes/compose.md)
