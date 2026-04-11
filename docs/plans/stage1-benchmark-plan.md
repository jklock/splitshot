# Stage1 Benchmark Parity Plan

## Goal

Use `Stage1.MP4` plus the user-provided Shot Streamer benchmark screenshot as a concrete acceptance benchmark for automatic detection quality.

## Benchmark Inputs

- Real benchmark file: `Stage1.MP4`
- Benchmark reference: Shot Streamer waveform and split-time result for the same stage video

## What The Benchmark Establishes

- Timer beep placement matters, not just shot count
- Total shot count matters
- Draw time matters
- Inter-shot split timing matters
- Stage time matters

## Product Change For This Pass

1. Add a benchmark-aware validation path in the repo.
2. Tune event extraction against the benchmark file.
3. Keep the detector local and ML-backed for shot classification.
4. Use the benchmark to verify timing behavior, not just synthetic fixtures.

## Implementation Areas

### Detection

- Improve shot event extraction so one real shot maps to one event
- Improve timer-beep extraction on real match audio
- Preserve downstream project, waveform, merge, scoring, and export behavior

### Tests

- Add a benchmark test for `Stage1.MP4`
- Validate count, draw, stage time, and split pattern against the Shot Streamer reference with explicit tolerances

## Done Criteria

- `Stage1.MP4` analysis is materially aligned with the Shot Streamer benchmark
- The benchmark lives in repo as a test, not only as a screenshot
- Existing tests remain green
