# Timeline

The timeline package organizes shot detections into a table of split rows and derived timing totals.

## Files

- [model.py](model.py) defines `SplitRow` and the timing helpers.

## Key Functions

- `sort_shots` returns shots ordered by `time_ms`.
- `compute_split_rows` converts the ordered shot list into `SplitRow` records.
- `draw_time_ms` returns the time from beep to first shot.
- `stage_time_ms` returns the time from beep to last shot.
- `raw_time_ms` is the same value as `stage_time_ms` in the current model.
- `average_split_ms` averages the non-empty split gaps between shots.
- `total_time_ms` returns the absolute time of the last shot.

## Browser Usage

The browser UI uses the split rows for the timing table, the split cards, and the waveform shot labels. The stage presentation layer consumes the same helpers to build its summary cards.