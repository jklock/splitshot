# Presentation

<!-- Documentation reviewed: 2026-08-11 -->

This package owns the derived stage metrics and timing summaries that the browser shell displays.

## Purpose

Use it when the change affects timing cards, stage metrics, dashboard summaries, or any derived presentation object built from the shared project state.

## Read This First

- [stage.py](stage.py)
- [popups.py](popups.py)

## Main Files

- [stage.py](stage.py): stage metrics, timing segments, and `build_stage_presentation`
- [popups.py](popups.py): popup and marker presentation helpers

## Runtime Flow

1. Read and sort the current shot list.
2. Derive draw, split, raw, and stage timing metrics.
3. Build formatted presentation objects for the browser state.

## Key Extension Points

- `build_stage_presentation`
- popup presentation helpers

## Related Tests

- [../../../tests/presentation/](../../../tests/presentation/)
- [../../../tests/browser/test_metrics_e2e.py](../../../tests/browser/test_metrics_e2e.py)

## Related Docs

- [../../../docs/userfacing/panes/metrics.md](../../../docs/userfacing/panes/metrics.md)
- [../../../docs/project/ARCHITECTURE.md](../../../docs/project/ARCHITECTURE.md)
