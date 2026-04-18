# Subagent TODO: Score and Metrics

This packet is one equal-priority branch of the left-pane remediation program defined in [LEFT_PANE_IMPLEMENTATION_SPEC.md](LEFT_PANE_IMPLEMENTATION_SPEC.md).

## Mission

Complete all remaining Score-pane and Metrics-pane remediation items while preserving the current scoring UI, imported-stage surface, and metric export formats.

## Owned Scope

Primary browser client ownership in `src/splitshot/browser/static/app.js`:

- `renderScoringShotList`
- `renderScoringPenaltyFields`
- `renderPractiScoreSummaries`
- `buildMetricsRows`
- `renderMetricsPanel`
- `buildMetricsCsv`
- `buildMetricsText`

Primary backend ownership:

- `src/splitshot/scoring/logic.py`
- `src/splitshot/browser/state.py`

Preferred new test files:

- `tests/browser/test_scoring_metrics_contracts.py`
- `tests/scoring/test_scoring_metrics_contracts.py`

## Do Not Expand Into

- project lifecycle or import-path behavior in the Project packet
- timing selection or threshold behavior in the Splits packet
- merge/export snapshot logic in the Merge and Export packet
- overlay text-box or drag behavior in the Overlay and Review packet

## TODO Checklist

- [ ] Formalize the imported-stage precedence contract versus manual shot edits.
- [ ] Harden preset-switch compatibility for penalty fields.
- [ ] Protect score-restore behavior after reanalysis or shot mutation.
- [ ] Lock the Score-to-Metrics summary contract.
- [ ] Lock imported-stage scoring-context freshness in Metrics.
- [ ] Define beep-null and missing-data projection behavior.
- [ ] Keep confidence display fresh after reanalysis.
- [ ] Ensure Metrics exports reflect the same current derived state as the pane.

## Implementation Plan

### 1. Characterize imported-stage plus manual-edit behavior

- Add tests for imported-stage scoring with manual shot edits still allowed.
- Preserve the current Official Raw, Video Raw, and Raw Delta behavior unless a separate product decision changes the user contract.
- Make summary source-of-truth rules explicit in `scoring/logic.py`.

### 2. Normalize preset-switch cleanup without changing presets themselves

- Capture current behavior when switching between supported scoring profiles.
- Explicitly clear or retain penalty fields using one deterministic ruleset.
- Preserve current preset ids, visible preset choices, and shot-row layout.

### 3. Harden restore semantics

- Add tests for restore after shot move, delete, and reanalysis.
- Ensure restore targets the current valid shot identity and does not revive incompatible stale penalty state.

### 4. Collapse Score and Metrics onto the same summary contract

- Ensure Score and Metrics consume the same `scoring_summary` fields.
- Prevent local Metrics-only recomputation of overlapping values.
- Keep metric labels and export text structure exactly as they are today.

### 5. Lock imported-stage freshness in Metrics

- Ensure Metrics rerenders when imported-stage source, stage number, competitor name, or competitor place changes.
- Preserve current wording and display labels.

### 6. Define missing-data policy

- Characterize current behavior for missing beep, missing raw time, missing imported-stage data, and empty confidence values.
- Normalize blank versus unavailable versus numeric zero in one place.
- Use the same policy for rendered Metrics, CSV export, and text export.

### 7. Tighten confidence refresh behavior

- Characterize Metrics before and after threshold reanalysis and primary reimport.
- Ensure stale confidence values are never reused after a new analysis result arrives.

### 8. Assert export parity for Metrics outputs

- Ensure CSV and text exports use the same current row model as the pane.
- Keep current filenames, columns, and textual headings unchanged.

## Risk Prevention

- Do not change current score letters, preset ids, or metric labels.
- Do not redesign the scoring pane layout.
- Do not change the current imported-stage mismatch surface unless a product decision explicitly says to do so.
- Prefer new targeted tests over editing the existing giant browser contract files.

## Validation

- `pytest tests/browser/test_scoring_metrics_contracts.py`
- `pytest tests/scoring/test_scoring_metrics_contracts.py`
- `pytest tests/browser/test_browser_static_ui.py -k "Official Raw or Video Raw or Raw Delta or metrics"`

## Handoff Requirements

- List changed files.
- State whether any visible Score or Metrics behavior changed. The expected answer is no.
- List tests run and results.
- Record any dependency on imported-stage behavior owned by the Project packet.