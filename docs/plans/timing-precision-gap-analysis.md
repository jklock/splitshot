# Timing Precision Gap Analysis

## Gap 1: ML Window Centers Are Coarse

Current shot timestamps are model window centers. That is robust for finding events, but it is not ideal for matching timer raw times to within a few milliseconds.

Closure:

- Add audio-level timestamp refinement after model peak selection.

## Gap 2: Raw-Time Tests Are Too Loose

Current raw-time tolerance allows 120 ms. That proves broad alignment but not precision parity.

Closure:

- Tighten the Stage1-4 raw-time tolerance after refinement.

## Gap 3: CSV Uses Correct Metric But Needs Precision Refresh

The CSV now includes `raw_time_*`, but it must be regenerated after detector precision changes.

Closure:

- Regenerate `artifacts/stage_suite_analysis.csv`.

## Gap 4: Documentation Needs Evidence

The audit should show before/after raw-time deltas so precision improvements are explicit.

Closure:

- Add a final precision audit with raw-time comparison and validation results.
