# Subagent TODO: Splits and Waveform

This packet is one equal-priority branch of the left-pane remediation program defined in [LEFT_PANE_IMPLEMENTATION_SPEC.md](LEFT_PANE_IMPLEMENTATION_SPEC.md).

## Mission

Complete all remaining Splits-pane and waveform remediation items while preserving the current timing editor, selected-shot behavior, and threshold workflow.

## Owned Scope

Primary browser client ownership in `src/splitshot/browser/static/app.js`:

- `splitRowForShot`
- `resolvedSplitMsForShot`
- `renderTimingEventList`
- `renderTimingEventEditor`
- `addTimingEvent`
- `renderTimingTable`
- `renderTimingTables`
- `renderSelection`
- `setTimingExpanded`
- `autoApplyThreshold`
- `scheduleThresholdApply`

Primary backend ownership:

- `src/splitshot/timeline/model.py`
- `src/splitshot/presentation/stage.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/ui/controller.py`

Preferred new test files:

- `tests/browser/test_timing_waveform_contracts.py`
- `tests/presentation/test_timing_contracts.py`

## Do Not Expand Into

- project path and lifecycle behavior in the Project packet
- scoring-summary rules in the Score and Metrics packet
- merge/export preview behavior in the Merge and Export packet
- overlay or review serializer behavior in the Overlay and Review packet

## TODO Checklist

- [ ] Prevent selected-shot orphaning after delete or reanalysis.
- [ ] Preserve user context when threshold reanalysis replaces timing state.
- [ ] Validate timing-event anchors after shot deletion and movement.
- [ ] Keep waveform and timing-table selection in sync under all navigation paths.

## Implementation Plan

### 1. Characterize current selection behavior everywhere

- Add tests covering table clicks, waveform clicks, drag, nudges, delete, restore, threshold change, and reanalysis.
- Treat selected-shot state as the single authority for waveform highlight, selected-shot panel, and timing row highlight.

### 2. Prevent orphaned selection

- Revalidate selected-shot id after destructive timing mutations and after reanalysis.
- If the selected shot no longer exists, choose a deterministic fallback target.
- Preserve current visible selection affordances and control labels.

### 3. Preserve user context across threshold reanalysis

- Keep threshold control behavior and debounce timing unchanged.
- Keep the timing workbench state stable when possible.
- Restore the same shot when it still exists, otherwise fall back using one deterministic rule.

### 4. Tighten timing-event anchor validation

- Revalidate events after shot move, delete, and reanalysis.
- Reject only truly invalid anchors; preserve valid timing-event workflows.
- Keep event editor controls and labels unchanged.

### 5. Keep waveform and table in sync

- Ensure the same selected-shot id drives both waveform and table render paths.
- Remove any local fallback selection behavior that can diverge between the two surfaces.

## Risk Prevention

- Do not redesign the timing workbench or waveform controls.
- Do not rename timing DOM ids or keyboard behaviors.
- Keep the current `0.00` timing edit format and column sizing behavior intact.
- Avoid touching unrelated scoring or overlay behavior while working in shared render paths.

## Validation

- `pytest tests/browser/test_timing_waveform_contracts.py`
- `pytest tests/presentation/test_timing_contracts.py`
- `pytest tests/analysis/test_analysis.py -k "timing or detection_threshold or delete_timing_event"`
- `pytest tests/presentation/test_presentation.py`

## Handoff Requirements

- List changed files.
- State whether any visible Splits or waveform behavior changed. The expected answer is no.
- List tests run and results.
- Record any dependency on browser-state or presentation contracts that could affect the Metrics packet.