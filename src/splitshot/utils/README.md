# Utils

The utils package contains the small shared helpers that do not belong to a larger domain area.

## Files

- [time.py](time.py) provides simple numeric and formatting helpers.

## Helpers

- `clamp` bounds a numeric value between a minimum and maximum.
- `ms_to_seconds` converts milliseconds to seconds.
- `seconds_to_ms` converts seconds to milliseconds.
- `format_time_ms` renders a millisecond value as `MM:SS.mmm` or a placeholder for missing values.

## Usage

These helpers are used by the analysis, presentation, browser, and export layers wherever a small time conversion or display formatting helper is needed.

**Last updated:** 2026-04-13
**Referenced files last updated:** 2026-04-10
