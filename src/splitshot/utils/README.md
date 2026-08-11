# Utils

<!-- Documentation reviewed: 2026-08-11 -->

This package owns small shared helpers that do not justify a larger subsystem.

## Purpose

Use it for compact utility functions that are reused across multiple layers and do not belong more naturally in analysis, browser, scoring, or export.

## Read This First

- [time.py](time.py)

## Main Files

- [time.py](time.py): numeric clamps, millisecond conversions, and display formatting helpers

## Key Extension Points

- `clamp`
- `ms_to_seconds`
- `seconds_to_ms`
- `format_time_ms`

## Related Tests

- covered indirectly by browser, presentation, analysis, and export tests

## Related Docs

- [../../../docs/project/ARCHITECTURE.md](../../../docs/project/ARCHITECTURE.md)
- [../presentation/README.md](../presentation/README.md)
