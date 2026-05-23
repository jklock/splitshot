# Execution Order

## 1. Audit Current UI And Preserve Proof

Inspect current code, current routes, and current screenshots. Do not start by polishing individual panels.

Closeout:

- gap matrix updated
- current screenshot audit linked
- baseline risks known.

## 2. Split Shell And View Architecture

Create explicit view-level structure before improving view details.

Use this migration order so the app is never broken for more than one verified slice:

### Phase 1a: Wrap

Add `activeView` state and view-container wrappers in `index.html`. Do not remove existing elements. Use `[hidden]` or `.view-hidden` to show/hide views. Verify existing sacred tests still pass or document exact DOM-update needs.

### Phase 1b: Move

Move existing `[data-surface-panel="single"]`, `[data-surface-panel="multi"]`, and `[data-surface-panel="library"]` content into the appropriate view containers without changing behavior. Verify.

### Phase 1c: Hide

Hide `.tool-rail` in Match and Library views while keeping it available in Stage. Verify rail-specific tests and update only tests whose assertions intentionally changed.

### Phase 1d: Retire

Only after the prior steps pass, remove the permanent global automation strip from the shell and keep controls in owning views. Verify before building new view features.

Closeout:

- Landing, Stage, Match, Library mount separately
- shared shell/context remains
- Stage panes preserved
- permanent global automation strip removed.

## 3. Landing Page

Build the front door and verify clean entry to all views.

## 4. Stage Video Edit Refinement

Preserve and simplify the current deep editor; integrate output and multi-angle workflows.

## 5. PiP, Waveform, Multi-Angle Stabilization

Fix preview sync and build waveform/multi-angle features before Match composite workflows rely on them.

## 6. Match Video Edit

Build the workspace frontend, Setup Once Apply Everywhere, recap, composite, and batch export.

## 7. Performance Library

Build the historical analytics frontend and automatic history integration.

## 8. Export And Output Workflows

Complete Stage, batch, recap, and composite exports with progress and completion states.

## 9. Integration Polish

Fix cross-view transitions, responsive behavior, accessibility, error states, and visual quality.

## 10. Proof, Regression, Release

Run required tests, capture empty and loaded screenshots, update proof docs, and close readiness gate.
