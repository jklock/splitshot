# Stage1 Benchmark Gap Analysis

## Current State

The synthetic tests prove the detector pipeline works, but the first pass on `Stage1.MP4` showed a large real-world gap:

- timer beep was misplaced
- shot count was over-reported
- real shots were split into multiple detections

## Gaps

### Benchmark Fidelity

- No test currently uses the real benchmark file
- The screenshot benchmark was not encoded into repo expectations

### Event Extraction

- Model probabilities were being converted to events too aggressively
- Shot grouping was not tight enough for real reverberant match audio
- Timer-beep extraction on quiet real audio was not robust enough

## Closure Plan

1. Add benchmark expectations derived from the Shot Streamer result.
2. Reduce duplicate shot detections through stronger event suppression/grouping.
3. Improve beep extraction in the pre-shot region.
4. Add a real benchmark test for `Stage1.MP4`.
5. Audit the final output against the benchmark.
