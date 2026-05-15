# Benchmarks

This package owns benchmark-oriented stage analysis and CSV export helpers.

## Purpose

Use it when comparing detector output across known reference clips or exporting benchmark summaries for analysis outside the app.

## Read This First

- [stage_suite.py](stage_suite.py)
- [cli.py](cli.py)

## Main Files

- [stage_suite.py](stage_suite.py): stage benchmark definitions, analysis helpers, CSV writer
- [cli.py](cli.py): benchmark CSV entrypoint

## Runtime Flow

1. Resolve the benchmark video set.
2. Run the normal analysis pipeline on each video.
3. Derive stage timing fields and confidence values.
4. Write the combined CSV output.

## Key Extension Points

- `default_stage_paths`
- `analyze_stage`
- `write_stage_suite_csv`

## Related Tests

- [../../../tests/benchmarks/](../../../tests/benchmarks/)

## Related Docs

- [../../../scripts/export/export_stage_suite_csv.py](../../../scripts/export/export_stage_suite_csv.py)
- [../../../docs/tests/TEST_SUITE_GUIDE.md](../../../docs/tests/TEST_SUITE_GUIDE.md)
