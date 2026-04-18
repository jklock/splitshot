# Subagent TODO: Overlay and Review

This packet is one equal-priority branch of the left-pane remediation program defined in [LEFT_PANE_IMPLEMENTATION_SPEC.md](LEFT_PANE_IMPLEMENTATION_SPEC.md).

## Mission

Complete all remaining Overlay-pane and Review-pane remediation items while preserving current badge styling, review text-box behavior, and exported overlay output.

## Owned Scope

Primary browser client ownership in `src/splitshot/browser/static/app.js`:

- `readOverlayPayload`
- `syncOverlayPreviewStateFromControls`
- `previewOverlayControlChanges`
- `setOverlayTextBoxField`
- `renderTextBoxEditors`
- `beginTextBoxDrag`
- `beginOverlayBadgeDrag`
- `renderLiveOverlay`
- `scheduleOverlayApply`

Primary backend ownership:

- `src/splitshot/browser/server.py`
  Route `/api/overlay`
- `src/splitshot/ui/controller.py`
- `src/splitshot/overlay/render.py`

Preferred new test files:

- `tests/browser/test_overlay_review_contracts.py`
- `tests/export/test_merge_export_contracts.py` or `tests/export/test_export.py` for narrowly scoped overlay parity additions

## Do Not Expand Into

- project lifecycle behavior in the Project packet
- scoring-summary logic in the Score and Metrics packet
- timing selection or threshold behavior in the Splits packet
- merge preview and export snapshot behavior in the Merge and Export packet

## TODO Checklist

- [ ] Lock browser overlay payload parity with backend overlay rendering.
- [ ] Harden delayed color-commit behavior.
- [ ] Formalize the lock-to-stack versus explicit-coordinate contract.
- [ ] Lock score-token color persistence to live badge rendering.
- [ ] Lock imported-summary availability and default box behavior across import and reopen flows.
- [ ] Harden post-drag `review_boxes_lock_to_stack` semantics.
- [ ] Preserve inspector scroll position through overlay round trips.
- [ ] Ensure drag-state cleanup always completes after canceled or interrupted interactions.

## Implementation Plan

### 1. Characterize browser preview versus export parity

- Add tests and export checks for current badge style, font size, bubble size, custom box geometry, lock-to-stack, and imported-summary placement.
- Ensure preview serialization and backend rendering consume the same field meanings.

### 2. Tighten color commit behavior

- Characterize picker open, preview, commit, cancel, blur, reopen, and export.
- Preserve the current picker UI while making preview-only versus committed state explicit.

### 3. Define one lock-to-stack precedence rule

- Characterize drag then toggle for badges and text boxes.
- Apply the same precedence rule in preview, persisted overlay payload, and export rendering.
- Preserve current controls and labels.

### 4. Lock score-token color persistence

- Characterize current score-color grid behavior in preview, reopen, and export.
- Ensure preview and export use the same token mapping.

### 5. Make imported-summary availability deterministic

- Characterize import, reopen, project replace, and missing-imported-stage cases.
- Ensure imported-summary UI and default box behavior match the current imported-stage state exactly.

### 6. Harden review lock-to-stack after drag

- Characterize text-box drag followed by `review_boxes_lock_to_stack` changes.
- Keep current visible controls while making the resulting behavior deterministic.

### 7. Preserve review inspector scroll position

- Characterize multi-card editing and overlay rerender loops.
- Preserve the current card order and scroll location through rerenders.

### 8. Guarantee drag cleanup on all exit paths

- Characterize cancel, blur, pane switch, rerender, and lost pointer capture during drag.
- Ensure all transient drag state is cleared every time.

## Risk Prevention

- Do not redesign the overlay or review panes.
- Do not rename overlay DOM ids, text-box field names, or `/api/overlay` payload keys.
- Preserve current imported-summary defaults, above-final behavior, and review card structure.
- If preview/export parity changes are needed, prove them with both export tests and the browser interaction audit.

## Validation

- `pytest tests/browser/test_overlay_review_contracts.py`
- `pytest tests/export/test_export.py -k overlay`
- `pytest tests/browser/test_browser_static_ui.py -k "text box or overlay or review"`
- `python scripts/audits/browser/run_browser_interaction_audit.py --browser chromium --report-json logs/browser-interaction-audit-test-videos-overlay-review.json`

## Handoff Requirements

- List changed files.
- State whether any visible Overlay or Review behavior changed. The expected answer is no.
- List tests run and results.
- Record any unresolved preview/export parity hotspot.