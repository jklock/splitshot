# Timeline

This package owns split-row generation and the core timing helpers derived from the shot list.

## Purpose

Use it when the change affects draw time, split calculations, stage time, shot ordering, or any timing table values shared across browser, metrics, and export views.

## Read This First

- [model.py](model.py)

## Main Files

- [model.py](model.py): split-row structures and timing helpers

## Runtime Flow

1. Sort shots by `time_ms`.
2. Build split rows and derived timing totals.
3. Feed the browser state, metrics, and presentation layers from the same timing helpers.

## Key Extension Points

- `sort_shots`
- `compute_split_rows`
- `draw_time_ms`
- `stage_time_ms`
- `average_split_ms`

## Related Tests

- [../../../tests/presentation/test_timing_contracts.py](../../../tests/presentation/test_timing_contracts.py)
- [../../../tests/browser/test_timing_waveform_contracts.py](../../../tests/browser/test_timing_waveform_contracts.py)

## Related Docs

- [../../../docs/userfacing/panes/splits.md](../../../docs/userfacing/panes/splits.md)
- [../presentation/README.md](../presentation/README.md)
