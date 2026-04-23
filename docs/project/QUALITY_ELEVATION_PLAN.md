# SplitShot Quality Elevation Plan

This plan focuses the next quality pass on three product standards:

1. Stability: controls keep state, do not collapse unexpectedly, do not jitter, and survive import/save/reopen/export flows.
2. Ease of use: the user can finish the common workflow quickly without hidden steps or confusing controls.
3. WYSIWYG: browser preview, saved project state, exported video, docs, and screenshots agree.

Phase 4-style visual expansion for PopUp, such as many new decoration presets and advanced typography, is intentionally deferred. The immediate goal is to make the current app feel dependable and fast before broadening the feature surface.

## PopUp Feature Plan

PopUp is a flagship feature. It should feel like a callout authoring system, not just a list of configurable boxes. The feature already supports shot-linked callouts, time-based callouts, score-derived text, custom placement, per-bubble style, motion paths, preview, export, and persistence. The next work should strengthen that foundation.

### Phase 1: Stability And WYSIWYG Foundation

Goal: every PopUp behavior should have one product meaning and one tested preview/export result.

Stability work:

- Extract shared popup semantics into a small tested domain layer:
  - effective start time
  - visible window
  - shot-linked score text
  - penalty text formatting
  - motion interpolation
  - normalized placement
  - explicit and auto size rules
- Keep browser JavaScript as UI glue and the Python renderer as the export painter, but make both conform to the same contract tests.
- Add regression coverage for:
  - card click selects and seeks without expanding
  - chevron selects, seeks, and toggles expansion
  - rendered bubble drag selects without opening the editor
  - time-based popup start/duration
  - shot-linked popup start/duration
  - scoring edits updating shot-linked popup text
  - motion path interpolation at start, middle, and end
  - save/reopen preserving popup state
  - export rendering matching preview-visible text, time, size, and position
- Add a focused browser audit for PopUp interactions, similar to the broader UI surface audit.
- Remove dead template or duplicate popup markup if the live editor no longer uses it.

Ease-of-use work:

- Make selection, seek, expansion, and drag rules explicit and consistent:
  - card title/header: select and seek
  - chevron: select, seek, expand/collapse
  - rendered bubble: select and drag
  - form controls: edit only
- Preserve scroll position while editing fields, toggling cards, and dragging rendered bubbles.
- Keep the selected bubble visible in the editor after drag and after seek.
- Add empty/error states for missing shots, missing score text, missing primary media, and no visible popup at the playhead.

WYSIWYG work:

- Ensure preview and export use identical text resolution for IDPA, USPSA, IPSC, and penalty combinations.
- Ensure preview and export use identical motion interpolation and clamping.
- Ensure preview and export agree on explicit width/height and auto-size behavior.
- Update PopUp docs and screenshots after behavior is finalized.

Exit criteria:

- A user can import shots, select any popup, drag it, edit duration, enable motion, save/reopen, and export without state loss or visual mismatch.
- PopUp browser interaction audit passes.
- PopUp preview/export parity tests pass.
- PopUp documentation describes the actual click behavior.

### Phase 2: Ease-Of-Use Authoring Layer

Goal: make PopUp fast to author for real match videos with many shots.

Stability work:

- Add a non-destructive popup timeline strip in the PopUp pane.
- Treat each popup as a timeline object with start, end, duration, enabled state, and selected state.
- Keep card state and timeline state synchronized through one selection model.
- Make bulk actions transactional so partial failures do not leave inconsistent local/server state.

Ease-of-use work:

- Add a compact popup timeline strip:
  - one bar per popup
  - start/end handles
  - selected state
  - enabled/disabled visual state
  - shot-linked marker label
  - current playhead marker
- Add fast controls:
  - play selected popup window
  - loop selected popup
  - jump to previous/next popup
  - set duration for selected/all/imported
  - enable/disable selected/all
  - delete selected
  - duplicate selected
- Add filters:
  - all
  - enabled
  - disabled
  - shot-linked
  - time-based
  - has motion
  - missing text
  - visible at playhead
- Add import options:
  - import all shots
  - import only scored shots
  - import only penalty/miss/no-shoot shots
  - refresh existing imported shot popups without touching manual bubbles
- Add inline summaries that show each popup's visible text, start, duration, anchor, and motion state without opening the full editor.

WYSIWYG work:

- Timeline bars should use the same effective time and visible window as preview/export.
- Play selected popup window should scrub the exact duration exported later.
- Import options should preserve existing style and motion choices unless the user explicitly chooses to reset them.

Exit criteria:

- A user can manage dozens of shot-linked popups without opening every card.
- The timeline strip makes popup overlap and missing visibility obvious.
- Bulk actions are covered by save/reopen and API tests.

### Phase 3: Motion Keyframe Editor

Goal: turn motion paths from an advanced form into an intuitive keyframe editor.

Stability work:

- Replace fixed mental model of "point counts" with explicit keyframes while preserving backward compatibility with existing motion_path data.
- Store keyframes with offset, x, y, and easing.
- Migrate existing motion paths into linear keyframes.
- Keep renderer fallback behavior for older projects.
- Add tests for keyframe insertion, deletion, reorder-by-time, interpolation, save/reopen, and export parity.

Ease-of-use work:

- Show keyframe dots over the video for the selected popup.
- Draw a path preview between keyframes.
- Let users:
  - add keyframe at playhead
  - delete selected keyframe
  - drag any keyframe directly on the video
  - jump previous/next keyframe
  - copy motion from previous popup
  - apply one motion path to selected imported popups
- Keep the base popup point and later keyframes visually distinct.
- Replace "Go" point rows with a compact keyframe list:
  - time offset
  - easing
  - X/Y
  - jump button
  - delete button
- Add easing:
  - linear
  - hold
  - ease in
  - ease out
  - ease in/out

WYSIWYG work:

- Browser path preview must match exported interpolation.
- Dragging a keyframe must update the live overlay immediately and persist through save/reopen.
- Export should render the selected easing exactly, or the UI should not expose that easing.

Exit criteria:

- A user can create a moving callout by scrubbing, adding keyframes, and dragging on the video without typing X/Y values.
- Existing projects with motion_path still load and export correctly.
- Preview/export parity is covered for all supported easing modes.

## Cross-App Audit Themes

The same problems seen in PopUp appear elsewhere in the app:

- Preview/export logic is split across browser JavaScript, Python render/export code, and persistence models.
- Expand/collapse and selection behavior is implemented feature-by-feature instead of through one shared pattern.
- Pane docs/screenshots can drift after behavior changes.
- Some controls are dense enough that users need stronger grouping, state summaries, and direct preview feedback.
- Resizable inspector and expanded workbench layouts need continuous browser audit coverage.

The pane plans below use the same structure as PopUp: stability, ease of use, and WYSIWYG.

## Project Pane Plan

Stability:

- Validate all path, project-folder, PractiScore, and primary-video flows through browser, API, persistence, and reopen tests.
- Make destructive flows explicit and recoverable where possible, especially New Project and Delete Project.
- Add tests for replacing primary media and confirming media-bound state resets predictably.
- Ensure status/progress messages cannot get stuck after failed imports.

Ease of use:

- Make the setup sequence obvious: primary video, optional PractiScore, project folder.
- Add stronger summaries after import: selected stage, competitor, official raw/final, and whether downstream panes now have context.
- Improve duplicate competitor/place selection so the user can identify the correct row quickly.
- Add validation messages near the relevant controls instead of only status-bar text.

WYSIWYG:

- Confirm imported PractiScore context is exactly what Score, Review, Overlay, Export, and Metrics consume.
- Keep Project docs/screenshots aligned with actual import and save behavior.
- Add a "current project state" summary that mirrors the saved bundle metadata.

## ShotML Pane Plan

Stability:

- Treat ShotML reruns and proposal generation as transactional operations with clear before/after state.
- Add tests for reset defaults, rerun analysis, generate proposals, apply proposal, discard proposal, and save/reopen.
- Guard advanced runtime controls from invalid combinations that can make analysis fail or hang.
- Ensure collapsed sections do not lose unsaved edited values.

Ease of use:

- Split controls into "basic", "tuning", and "advanced" modes so the pane does not feel like a wall of numeric fields.
- Add a detector outcome summary after every run: beep time, shot count, low-confidence count, suppressed/restored count.
- Add recommended next action hints based on common failures: missing quiet shots, extra echoes, shifted beep, fast-pair suppression.
- Make proposal rows easier to scan with reason, current time, proposed time, delta, confidence, and direct preview jump.

WYSIWYG:

- Ensure ShotML confidence and source labels match Splits and Metrics.
- Ensure applying proposals updates waveform, timing table, metrics, and export inputs consistently.
- Update docs/screenshots whenever section grouping or proposal behavior changes.

## Splits And Waveform Plan

Stability:

- Centralize shot selection, waveform marker selection, timing table selection, and video seek behavior.
- Add browser tests for nudge, drag marker, add shot, delete shot, expanded timing edit, event insertion, waveform zoom/pan, and save/reopen.
- Keep waveform drag performance smooth with throttled rendering and clear commit boundaries.
- Ensure low-confidence/manual/restored/deleted shot state cannot desync between table, waveform, score rows, and metrics.

Ease of use:

- Make selected shot context denser but clearer: shot number, total, split, source, confidence, score, and visible nudge controls.
- Add previous/next shot navigation.
- Add a visible "Add Shot" mode indicator and a quick way back to Select.
- Make timing events easier to place by previewing their position before Add Event.

WYSIWYG:

- Timing changes must immediately update video overlay, PopUp shot anchors, Score shot rows, Review summaries, Export, and Metrics.
- Expanded and compact timing tables should show the same source data with different density, not different behavior.
- Screenshots and docs should reflect the current expanded/collapsed behavior.

## Score Pane Plan

Stability:

- Add coverage for enabling/disabling scoring, changing presets, per-shot score edits, penalty edits, restore, delete, and save/reopen.
- Ensure preset changes normalize existing scores and penalties without stale hidden values.
- Ensure Score delete/restore uses the same shot lifecycle as Splits.
- Guard against scoring rows desyncing when shots are added, removed, moved, or restored.

Ease of use:

- Keep shot-card header behavior consistent with PopUp and Review: select row vs expand controls should be explicit.
- Add compact scoring summaries per collapsed card: shot number, time, score, penalties, and status.
- Add bulk scoring helpers where appropriate, such as set unscored shots to default value.
- Improve imported context visibility so users know what official result they are comparing against.

WYSIWYG:

- Score text should match PopUp, Overlay score tokens, Review summary boxes, Metrics, and Export.
- Score-token color preview should match overlay/export rendering.
- Docs should call out exactly how shot-linked PopUps respond to scoring edits.

## PiP Pane Plan

Stability:

- Add browser/API/export tests for adding media, removing media, per-item expansion, default settings, per-item overrides, sync nudges, opacity, size, X/Y, and save/reopen.
- Ensure image and video sources share one consistent media-card lifecycle.
- Ensure drag-to-position in preview cannot produce invalid coordinates or stale export placement.
- Make missing media paths and failed loads visible per item.

Ease of use:

- Separate defaults from selected item editing more clearly.
- Add a per-item compact summary: file name, enabled/export state, layout, size, opacity, sync offset.
- Add direct preview affordances for selected PiP item, including outline and drag handle.
- Make sync nudging faster with play/loop around sync point.

WYSIWYG:

- Preview and export must agree for all layouts: picture-in-picture, side-by-side, and above/below.
- Per-item opacity, size, placement, and sync must render identically in browser and export.
- Docs/screenshots should show both defaults and per-item overrides.

## Overlay Pane Plan

Stability:

- Centralize overlay placement math for browser preview and export.
- Add tests for every stack direction, quadrant, custom coordinate, lock toggle, drag, badge size, style, color, opacity, font, and score-token color.
- Keep lock behavior consistent: if any locked item is dragged, the locked stack moves as one unit.
- Guard against inspector resize causing horizontal overflow or hidden controls.

Ease of use:

- Reduce visual complexity by grouping stack placement, locks, typography, badge styles, and score colors into clear collapsible sections.
- Add a small live placement summary showing stack anchor, flow, locked items, and custom status.
- Make disabled X/Y fields explain why they are disabled and what action enables them.
- Add reset buttons for placement and badge style groups.

WYSIWYG:

- Preview and export must agree for all badge geometry, typography, colors, opacity, score token coloring, and lock-to-stack behavior.
- Review visibility toggles should be reflected in overlay preview without changing the underlying style settings.
- Documentation screenshots should be regenerated after layout changes.

## PopUp Pane Plan

Use the dedicated PopUp Feature Plan above.

The pane-level audit criteria are:

- Stability: selection, expansion, drag, motion, imported shot refresh, save/reopen, and export parity.
- Ease of use: timeline strip, filters, bulk actions, loop selected popup, and keyframe editor.
- WYSIWYG: shared semantics for timing, text, placement, size, motion, and export.

## Review Pane Plan

Stability:

- Add tests for badge visibility toggles, add custom box, add summary box, expand/collapse, duplicate, remove, content source, lock-to-stack, drag, color, opacity, width/height, and save/reopen.
- Ensure Review text-box lock behavior uses the same stack-placement contract as Overlay.
- Ensure expand/collapse never fights selection, drag, or rerender.
- Guard against text boxes overflowing the video frame after resize or export crop/aspect changes.

Ease of use:

- Add compact summaries for collapsed boxes: type, enabled state, lock state, placement, size, and first line of text.
- Add reset placement and reset style actions per box.
- Make imported summary state clear when PractiScore is missing or stale.
- Keep the add buttons and text-box list visually consistent with PopUp cards.

WYSIWYG:

- Review boxes must match preview/export for placement, stack lock, text wrapping, size, opacity, colors, and imported summary content.
- Summary boxes should use the exact same PractiScore/scoring context as Metrics and Export.
- Docs should distinguish Review text boxes from PopUp callouts clearly.

## Export Pane Plan

Stability:

- Add tests for preset changes, custom settings, output path validation, failed export, successful export, log modal, log export, and save/reopen.
- Validate settings before export starts and show specific field-level errors.
- Prevent duplicate concurrent exports unless explicitly supported.
- Keep export log status reliable after failure, cancel, and retry.

Ease of use:

- Add a preflight checklist before export:
  - primary video present
  - output path valid
  - FFmpeg available
  - PiP enabled state
  - overlay/review/popup visible state
  - estimated resolution/frame rate/container
- Add a draft/final intent selector that maps to sane bitrate/preset defaults.
- Keep advanced codec settings available but grouped below common export choices.
- Add direct links or jump actions to fix missing PiP, Review boxes, PopUps, or output path.

WYSIWYG:

- Export should render exactly what preview shows for timing, overlay, PopUp, Review, score, and PiP.
- Add automated preview/export pixel or geometry checks for representative projects.
- Documentation should list every visible feature included in export and every feature intentionally excluded.

## Metrics Pane Plan

Stability:

- Add tests for compact metrics, expanded metrics, CSV export, text export, PractiScore context, scoring context, timing edits, score edits, and save/reopen.
- Ensure the compact trend snapshot and expanded table use the same row builder.
- Ensure CSV/text export uses the same current state as the visible metrics.
- Keep expanded/collapsed layout stable under inspector resizing.

Ease of use:

- Make Metrics clearly read-only while providing source links or jump actions to fix values in Project, Splits, ShotML, or Score.
- Keep scoring context in a compact two-column table with all text visible.
- Add "copy summary" and "copy selected row" actions if they do not conflict with CSV/text export.
- Make trend snapshot scan-friendly: shot/event, split, total, score, confidence, action.

WYSIWYG:

- Metrics values should match Score, Splits, ShotML, Project, Review summaries, and Export metadata.
- CSV/text exports should match the visible table labels and values.
- Docs/screenshots should be updated any time column labels or scoring context layout changes.

## Shared UI Systems Plan

Stability:

- Build or enforce a shared card pattern for selectable/expandable rows:
  - one click target for selection/seek
  - one chevron for expand/collapse
  - form controls that never bubble into row actions
  - stable scroll preservation
- Build shared color-field and opacity-field layout rules used by Overlay, PopUp, Review, and Score color controls.
- Keep resize behavior covered by browser audits for rail, inspector, waveform, expanded timing, expanded metrics, and compact panes.

Ease of use:

- Normalize labels:
  - use `>` / `v` for expandable cards and sections
  - use text buttons only for commands
  - keep destructive buttons visually consistent
- Add concise summaries to collapsed dense cards.
- Keep controls grouped by user workflow rather than by internal model field.

WYSIWYG:

- Every feature that renders in export should have a preview parity contract.
- Every user-facing pane should have docs and current screenshots.
- Every screenshot update should be tied to a browser audit or Playwright capture so docs do not drift.

## Suggested Execution Order

1. PopUp Phase 1.
2. Shared selectable/expandable card pattern.
3. Overlay and Review parity cleanup.
4. Splits/Waveform stability pass.
5. PopUp Phase 2.
6. Score and Metrics consistency pass.
7. PiP preview/export parity pass.
8. Export preflight and logging pass.
9. PopUp Phase 3.
10. Documentation and screenshot refresh across all panes.

