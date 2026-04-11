# Timing Precision Final Audit

## What Changed

SplitShot now uses a two-stage detector:

1. ML classification finds the timer beep and shot events.
2. High-resolution signal refinement timestamps those selected events.

The refinement is generic and not hard-coded to Stage1-4:

- Beep time is refined to the first stable tonal onset in the detected beep region.
- Shot time is refined to the first strong transient in the ML-selected shot event.
- Confidence remains the ML probability.
- Shot count remains controlled by the ML event picker.

Current calibration:

- `BEEP_ONSET_FRACTION = 0.24`
- `SHOT_ONSET_FRACTION = 0.66`

## Raw-Time Results

The score screenshot `Raw` column is the benchmark metric. SplitShot exports this as `raw_time_s`.

| Stage | Reference Raw | Before | After | After Delta |
|---|---:|---:|---:|---:|
| Stage1 | 13.55 | 13.541 | 13.552 | +0.002 |
| Stage2 | 19.83 | 19.899 | 19.826 | -0.004 |
| Stage3 | 13.62 | 13.633 | 13.624 | +0.004 |
| Stage4 | 17.01 | 16.944 | 17.013 | +0.003 |

Before max absolute raw-time error:

```text
69 ms
```

After max absolute raw-time error:

```text
4 ms
```

Generated output:

- `artifacts/stage_suite_analysis.csv`

## Validation

Commands run:

```bash
uv run splitshot-benchmark-csv --output artifacts/stage_suite_analysis.csv Stage1.MP4 Stage2.MP4 Stage3.MP4 Stage4.MP4
uv run pytest
```

Results:

- Full test suite passed: `31 passed`.
- Stage1-4 raw benchmark tolerance tightened from 120 ms to 10 ms.
- Desktop smoke passed: `app-smoke-ok`.

## Risk

This improves precision against the current four real benchmark stages. Broader proof still requires more real match footage and side-by-side Shot Streamer exports.
