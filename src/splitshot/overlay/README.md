# Overlay

<!-- Documentation reviewed: 2026-08-11 -->

This package owns overlay badge and review-box rendering for preview and final export.

## Purpose

Use it when the change affects timer, shot, score, or review-box drawing, overlay layout rules, or export-time frame painting.

## Read This First

- [render.py](render.py)

## Main Files

- [render.py](render.py): `Badge`, `OverlayRenderer`, and overlay paint helpers

## Runtime Flow

1. Read current timeline and scoring state.
2. Build the active badge and text-box representation for the current frame.
3. Paint the overlay into preview or export output.

## Key Extension Points

- `OverlayRenderer`

## Related Tests

- [../../../tests/export/test_export.py](../../../tests/export/test_export.py)
- [../../../tests/browser/test_overlay_review_contracts.py](../../../tests/browser/test_overlay_review_contracts.py)

## Related Docs

- [../presentation/README.md](../presentation/README.md)
- [../../../docs/userfacing/panes/overlay.md](../../../docs/userfacing/panes/overlay.md)
