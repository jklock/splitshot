# Left Pane Remediation TODO

Derived from [LEFT_PANE_AUDIT.md](LEFT_PANE_AUDIT.md) and the current branch implementation state on 2026-04-18.

Execution specification: [LEFT_PANE_IMPLEMENTATION_SPEC.md](LEFT_PANE_IMPLEMENTATION_SPEC.md).

This backlog contains the left-pane audit items that are still open or only partially hardened. It intentionally excludes the risks already closed on the current branch.

All remaining items are equal execution priority. The severity labels below are risk labels only.

## Already Closed On This Branch

These audit risks were already converted into code and validation, so they are not repeated below as open TODOs:

- shared Review and Overlay text-box normalization for imported-summary and above-final placement
- split editor default width improvements, persisted column resizing, and `0.00` timing edit formatting
- imported official raw versus video raw clarity in the Score pane
- export snapshot flushing before `/api/export`
- merge-source `pip_size_percent` and `sync_offset_ms` serialization into export payloads
- active tool and baseline UI-state restore ordering
- repo-local bundled-media browser interaction audit coverage

## Risk Severity Legend

- High: user-visible state drift, destructive loss risk, or preview/output mismatch likely to make the product feel broken
- Medium: confusing editor behavior, stale projection risk, or parity gaps that are recoverable but visible
- Low: consistency or clarity hardening that is still required, but less likely to produce destructive user-visible breakage

## Non-Regression Rules

- Add characterization coverage before behavior changes. Capture the current behavior in [tests/browser/test_browser_control.py](../../tests/browser/test_browser_control.py), [tests/browser/test_browser_static_ui.py](../../tests/browser/test_browser_static_ui.py), [tests/persistence/test_persistence.py](../../tests/persistence/test_persistence.py), [tests/export/test_export.py](../../tests/export/test_export.py), [tests/scoring/test_scoring_and_merge.py](../../tests/scoring/test_scoring_and_merge.py), [tests/presentation/test_presentation.py](../../tests/presentation/test_presentation.py), and [tests/analysis/test_analysis.py](../../tests/analysis/test_analysis.py) before refactoring.
- Preserve current user contracts. Do not rename DOM ids, API routes, JSON keys, visible labels, or button flows unless the remediation explicitly requires a product change.
- Validate both browser and backend surfaces for cross-pane work. If a fix touches preview/export parity or derived projections, rerun the relevant browser suite plus the backend suite for that seam.
- Use real bundled-media audits for cross-pane behavior. When a change affects preview, export, PractiScore, or merge parity, rerun [scripts/audits/browser/run_browser_interaction_audit.py](../../scripts/audits/browser/run_browser_interaction_audit.py), [scripts/audits/browser/run_browser_export_matrix.py](../../scripts/audits/browser/run_browser_export_matrix.py), and the narrower browser audit that matches the touched surface.
- Ship one seam at a time. Avoid multi-pane refactors without a characterization baseline so any regression can be traced to one relationship change.

## Project Pane

- [ ] High: Freeze project detail draft and apply semantics across pane switches and save/open.
  Risk: typed project details can look committed in the Project pane but reopen as stale or partially applied after a cross-pane action.
  Preserve current behavior: characterize the current typing, pane-switch, save, and reopen flow in browser-control and persistence tests before refactoring; keep the current field values, autosave timing, and save/open button flow unchanged.

- [ ] High: Harden project-folder probe and chosen-path consistency.
  Risk: folder probe results can diverge from the chosen path and open the wrong project context or media state.
  Preserve current behavior: capture chooser-result to probe to use-folder round trips in browser-control tests and preserve the current browse/probe/apply user flow while tightening state validation.

- [ ] Medium: Lock PractiScore context reimport determinism.
  Risk: stage, competitor, and imported-summary context can drift on reimport, causing Score, Review, and Metrics to reflect a different imported source than the user expects.
  Preserve current behavior: characterize the current import and reimport flow in [tests/analysis/test_practiscore_import.py](../../tests/analysis/test_practiscore_import.py) and browser-control tests, then preserve the current field defaults and import summary text while hardening determinism.

- [ ] High: Contain primary-import side effects so unrelated pane state is not reset accidentally.
  Risk: importing or replacing primary media can reset selection, waveform, or derived pane state in ways that feel like other panes broke.
  Preserve current behavior: characterize the current post-import state for selection, active pane, and persisted UI state before changing initialization order; only remove accidental resets, not the intended fresh-import bootstrap behavior.

- [ ] Medium: Verify lifecycle restore behavior across new/open/save/delete flows.
  Risk: project lifecycle actions can still restore the wrong pane or partially reset expanded state under some orderings.
  Preserve current behavior: add lifecycle regression tests around the current landing pane and expanded-state behavior, then tighten restore ordering without changing where the user lands today.

## Score Pane

- [ ] High: Formalize the imported-stage precedence contract versus manual shot edits.
  Risk: the user can edit shot scoring while parts of the summary still come from imported official aggregates, which can look like the pane ignored the edit.
  Preserve current behavior: add characterization coverage for current manual-edit plus imported-summary behavior, then make the precedence rules explicit without changing existing visible totals unless the product decision changes.

- [ ] Medium: Harden preset-switch compatibility for penalty fields.
  Risk: switching presets can leave stale penalty fields or counts attached to shots in ways that are valid in persistence but confusing in the pane.
  Preserve current behavior: capture the current preset-switch rendering and persistence rules first, then preserve the same preset options and shot-row layout while tightening field cleanup rules.

- [ ] Medium: Protect score-restore behavior after reanalysis or shot mutation.
  Risk: restoring an original score after upstream shot movement, deletion, or reanalysis can revive the wrong prior value or fail silently.
  Preserve current behavior: characterize the current restore semantics around reanalysis and shot mutation in browser-control and scoring tests before touching controller logic; keep the restore button behavior and resulting visible scores stable.

- [ ] Medium: Lock the Score-to-Metrics summary contract.
  Risk: Score can remain correct while Metrics drifts if summary generation changes without matching projection updates.
  Preserve current behavior: add dual-pane assertions that the same scoring summary feeds both panes and keep the current visible metric labels and exported text layout unchanged.

## Splits Pane

- [ ] High: Prevent selected-shot orphaning after delete or reanalysis.
  Risk: the selected-shot panel can point at a deleted or re-derived shot and leave the user editing a stale selection.
  Preserve current behavior: characterize current delete and reanalysis selection handoff in browser-control and presentation tests; preserve today’s selection affordances and only harden the fallback target.

- [ ] High: Preserve user context when threshold reanalysis replaces timing state.
  Risk: threshold changes can rebuild timing state underneath the current selection and make the pane feel like it jumped to a different shot.
  Preserve current behavior: lock down current threshold-to-selection behavior in browser-control tests and keep the same threshold field, apply cadence, and visible workbench layout while improving state handoff.

- [ ] Medium: Validate timing-event anchors after shot deletion and movement.
  Risk: timing events can stay attached to invalid anchors and produce split rows that look correct in one surface but not another.
  Preserve current behavior: characterize current event-list and timing-table behavior before changing anchor validation; preserve the current event editor workflow and only reject truly invalid anchors.

- [ ] High: Keep waveform and timing-table selection in sync under all navigation paths.
  Risk: the waveform can highlight one shot while the table and selected-shot editor show another.
  Preserve current behavior: add end-to-end selection assertions covering table clicks, waveform clicks, nudges, and deletions; keep the current selected-shot visuals and keyboard/button flows unchanged.

## PiP Pane

- [ ] High: Lock live preview sync to persisted `sync_offset_ms` behavior.
  Risk: preview playback can show a different offset than the persisted merge source or export will use.
  Preserve current behavior: characterize current preview, persistence, and export state for merge offsets in browser-control, export, and real-browser interaction audits before tightening sync order.

- [ ] High: Guarantee drag interactions commit before autosave and export.
  Risk: a user can drag a PiP source to the right place, see it there, then export or reopen into an older position.
  Preserve current behavior: add characterization tests for current drag-end to autosave/export timing and keep the same drag affordance while making commit timing deterministic.

- [ ] Medium: Make non-PiP layout expectations explicit without changing existing layout behavior.
  Risk: side-by-side and above-below accept state that has weak live preview feedback, so users can assume export will match a preview that never actually existed.
  Preserve current behavior: do not change current layout math or controls during hardening; first add coverage that documents the current preview limitations and then add clarity without altering existing exports.

- [ ] Medium: Validate multi-source merge expectations beyond current source serialization.
  Risk: per-source state may persist correctly but still render in combinations the user did not expect when multiple sources and non-PiP layouts interact.
  Preserve current behavior: expand current export-matrix coverage around the existing merge layouts and preserve the present layout outputs while tightening tests around source ordering and offsets.

## Overlay Pane

- [ ] High: Lock browser overlay payload parity with backend overlay rendering.
  Risk: the on-screen overlay can look correct while export differs by font, bubble size, or placement.
  Preserve current behavior: add characterization tests and export comparisons for the current overlay styles before touching serializers or render math; keep the current visible overlay controls and output defaults stable.

- [ ] Medium: Harden delayed color-commit behavior.
  Risk: the color picker can show a new color in preview before the committed state or export reflects it.
  Preserve current behavior: characterize the current picker-open, preview, commit, and cancel flows first; keep the same picker UI and only make commit timing explicit and testable.

- [ ] Medium: Formalize the lock-to-stack versus explicit-coordinate contract.
  Risk: the user can drag a badge or box, toggle lock-to-stack, and get a result that is valid internally but does not match the user’s mental model.
  Preserve current behavior: add characterization coverage around current toggle and drag interactions, then preserve the current default lock states and coordinate controls while making precedence deterministic.

- [ ] Medium: Lock score-token color persistence to live badge rendering.
  Risk: saved score colors can differ between what the pane previews and what later renders on reload or export.
  Preserve current behavior: capture the current color-grid to badge rendering contract in browser-control and export tests before adjusting serialization; keep the visible color choices and styling scheme unchanged.

## Review Pane

- [ ] Medium: Lock imported-summary availability and default box behavior across import and reopen flows.
  Risk: imported-summary controls can appear or disappear at the wrong time, making the Review pane look inconsistent even when overlay state still exists.
  Preserve current behavior: characterize current add-imported-box, PractiScore import, reopen, and export flows first; keep the current imported-summary defaults and add/remove buttons unchanged while tightening availability rules.

- [ ] Medium: Harden post-drag `review_boxes_lock_to_stack` semantics.
  Risk: after dragging a text box, toggling lock-to-stack can produce a result the user experiences as a reset or ignored change.
  Preserve current behavior: add characterization tests around current drag then toggle sequences and preserve the same text-box controls and drag behavior while clarifying state precedence.

- [ ] Low: Preserve inspector scroll position through overlay round trips.
  Risk: editing one text box can bounce the inspector list and make the pane feel unstable even when state is preserved.
  Preserve current behavior: capture the current scroll retention behavior and card ordering before any render-path refactor; keep the current card structure and ordering stable.

- [ ] Medium: Ensure drag-state cleanup always completes after canceled or interrupted interactions.
  Risk: stale drag state can leave handles, cursor modes, or subsequent edits in a partially active interaction mode.
  Preserve current behavior: characterize cancel, blur, and interrupted drag flows in browser tests and preserve the existing drag affordances while making cleanup unconditional.

## Export Pane

- [ ] Medium: Lock export-path draft consistency.
  Risk: the export path field can show one value while the persisted export target or last-used value differs.
  Preserve current behavior: add characterization coverage for current typing, browse, preset change, save, and reopen behavior, then keep the same export-path field and browse flow while tightening persistence timing.

- [ ] Medium: Clarify preset versus custom-mode behavior without changing current render settings.
  Risk: users can move between preset and custom settings and lose track of which settings actually govern export.
  Preserve current behavior: first document the current preset/custom transitions in browser-control tests; preserve the current preset options and setting fields while making the mode boundaries explicit.

- [ ] Low: Prevent stale export-log state from looking like a current failure.
  Risk: old error text or logs can stay visible after a successful export and make the pane appear broken.
  Preserve current behavior: characterize the current log-open, close, successful export, and failed export flows first, then keep the same modal and log-download behavior while tightening freshness rules.

## Metrics Pane

- [ ] Medium: Lock imported-stage scoring-context freshness.
  Risk: Metrics can keep showing a stale imported-stage context after Score or PractiScore state changed.
  Preserve current behavior: add characterization coverage tying Metrics to the same imported context shown in Score and preserve the current metric labels and summary wording while tightening refresh triggers.

- [ ] Low: Define beep-null and missing-data projection behavior.
  Risk: Metrics can look stable while edge-case data silently collapses to blank or misleading values.
  Preserve current behavior: capture the current missing-data rendering and export behavior before normalizing edge cases; keep the current labels and only harden how empty values are derived.

- [ ] Medium: Keep confidence display fresh after reanalysis.
  Risk: reanalysis can update shot state while Metrics continues to project older confidence values.
  Preserve current behavior: characterize the current reanalysis-to-metrics refresh path and preserve the current wording and formatting while tightening refresh invalidation.

- [ ] Medium: Ensure Metrics exports reflect the same current derived state as the pane.
  Risk: CSV or text exports can match an older projection even when the pane has already rerendered to something else, or vice versa.
  Preserve current behavior: add direct assertions that pane rendering, CSV export, and text export all use the same current inputs; keep the current CSV/text structure and labels unchanged.

## Exit Criteria

- Every item above has a characterization test or real-browser audit that captures the current user-visible behavior before any remediation changes land.
- Each remediation is validated against the narrowest relevant suites first and then against the bundled-media browser audit when it touches cross-pane behavior.
- No remediation is considered complete if it changes current user-visible behavior without an explicit product decision documented alongside the change.