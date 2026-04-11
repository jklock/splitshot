# Timing Precision Plan

## Goal

Improve raw-time precision against the score screenshot `Raw` column without hard-coding per-stage results.

The target metric is:

```text
raw time = final shot time - timer beep time
```

## Current Evidence

Current SplitShot raw time is already close:

| Stage | Reference Raw | SplitShot Raw | Delta |
|---|---:|---:|---:|
| Stage1 | 13.55 | 13.541 | -0.009 |
| Stage2 | 19.83 | 19.899 | +0.069 |
| Stage3 | 13.62 | 13.633 | +0.013 |
| Stage4 | 17.01 | 16.944 | -0.066 |

The residual error is in the tens of milliseconds, which is consistent with using ML window centers instead of a refined audio event timestamp.

## Approach

1. Keep the ML model responsible for event classification and event count.
2. Add deterministic high-resolution timestamp refinement after ML event selection.
3. Refine shot times inside a small window around each ML event using local transient shape.
4. Refine beep time using tonal onset/energy inside the beep search region.
5. Keep safeguards so refinement cannot merge adjacent shots or jump to echo/noise far from the ML event.
6. Tighten raw-time tests once the refinement is stable.

## Precision Rules

- Shot refinement should prefer the earliest strong transient in the selected acoustic event, not the center of the ML window.
- The current generic calibration uses 66% of the local shot impulse peak.
- If a shot is part of a multi-peak impulse, choose the stable peak/onset closest to the shot timer convention.
- Refinement must stay within a bounded window around the ML detection.
- Beep refinement should use the first stable tonal rise inside the detected beep region.
- The current generic calibration uses 24% of the local beep tonal peak.
- Confidence still comes from the ML score.
- Manual edits remain exact user-specified times.

## Acceptance

- Stage1-4 raw-time deltas should be materially tighter than the previous maximum absolute error of 69 ms.
- Synthetic fixture tests must still pass.
- Shot counts must remain unchanged.
- Stage1 split benchmark must remain within accepted tolerance.
