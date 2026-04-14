# Benchmarks

The benchmarks package compares detector output across a set of stage videos and exports the results to CSV.

## Files

- [stage_suite.py](stage_suite.py) defines `StageBenchmark`, the stage analysis helpers, and the CSV writer.
- [cli.py](cli.py) exposes the benchmark exporter as `splitshot-benchmark-csv`.

## Workflow

1. `default_stage_paths` looks for `Stage1.MP4` through `Stage4.MP4` in the selected directory.
2. `analyze_stage` runs the full analysis pipeline for one video.
3. `write_stage_suite_csv` writes a wide CSV table with per-shot timing and confidence columns.
4. The CLI prints the output path and the number of analyzed rows.

## Output Shape

Each benchmark row includes:

- the stage name and file path
- beep, draw, raw, and average split timings
- per-shot absolute times and confidences
- split durations between shots
- cumulative beep-to-shot timings

## Notes

- The benchmark code uses the same analysis and presentation helpers as the application itself.
- The generated CSV in `artifacts/stage_suite_analysis.csv` is a convenience output, not a committed source file.

**Last updated:** 2026-04-13
**Referenced files last updated:** 2026-04-10
