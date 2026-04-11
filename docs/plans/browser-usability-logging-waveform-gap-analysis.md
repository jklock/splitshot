# Browser Usability Logging Waveform Gap Analysis

## Current Gaps

- There is no per-run activity log, so UI behavior cannot be audited after a session.
- The right sidebar shows command buttons that are not contextual to the active tool.
- The left rail has a useless bottom New button.
- The left rail text is small and low contrast.
- The logo is still visually undersized inside the brand cell.
- Metrics are in the right sidebar instead of a thin always-visible status strip.
- The selected-shot controls appear regardless of active tool.
- Waveform clicks add shots accidentally and do not support an explicit select/edit workflow.
- The waveform cannot expand into a large editing surface.
- Timing cannot expand into a large editing surface.
- Current tests verify markup presence more than actual intended workflow behavior.

## Closure Plan

- Add an `ActivityLogger` that writes JSONL records to console and `logs/`.
- Add `/api/activity` so browser-side actions are persisted in the same run log.
- Move metrics into a single top strip and remove non-contextual command controls.
- Move primary/secondary file open actions into the Project and Merge panes only.
- Remove the rail New button and keep project creation in the Project pane.
- Scope selected-shot controls to review/timing/edit workflows.
- Add waveform expand/select/add/beep/drag/keyboard editing.
- Add timing expand/collapse with a center workbench table.
- Update tests around user-visible feature behavior and observability.

## Residual Risks

- Browser-native video controls still differ by browser.
- Without a real browser automation dependency, tests can verify server behavior and JavaScript wiring but not pixel-level pointer motion.
- Verbose logging can produce large files during long review sessions; this is intentional until logging is explicitly disabled later.
