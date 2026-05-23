> **Note:** Historical ledger; invalidated by later audit. Do not execute this package. Migrate still-valid requirements into Automate3 only.


# Execution Order

This is the same-day dependency order for completing the UI overhaul.

## 0. Preserve The `v1.0.5` Baseline

Reason:

- `main` is now the shipped floor.
- UI work must not regress the released Windows export-font path, OCR proof path, or packaged fixture workflow.

Closeout:

- targeted export/static UI proof for font-stack and export-baseline behavior
- no workflow regression around `docs/Clip1.MP4`

## 1. PiP Performance And Merge Editor

Reason:

- The current PiP preview is too jumpy to sync visually.
- If preview playback is not trustworthy, merge and Stage Composite UI work is blocked by a broken interaction foundation.

Closeout:

- smooth preview playback
- bounded drift correction
- reseek only on defined boundaries
- drag without heavy render/sync churn

## 2. Landing Page

Reason:

- The landing page is the user's first impression.
- It must exist before other surfaces can be properly navigated.

Closeout:

- three entry cards
- recent activity
- quick-start shortcuts
- empty state

## 3. Shell Navigation And Surface Model

Reason:

- The shell still presents the old flat tool rail.
- The rest of the UI needs correct top-level surface framing before pane-specific work lands.

Closeout:

- top-level surface switcher
- context header
- mode-aware pane model
- Landing Page integration

## 4. Stage Video Edit UI

Reason:

- Existing stage-edit panes already exist and can be reorganized and extended first.
- Output profiles are the clearest visible gap between backend completion and user usability.

Closeout:

- output-profile manager with preview
- stage output configuration UI
- render-plan and retained-review source UX
- multi-angle features

## 5. Waveform And Timeline Enhancements

Reason:

- Multi-track waveform and color-coded segments are needed for multi-angle work.
- They depend on the shell model but not on match workspace UI.

Closeout:

- multi-track waveform
- color-coded segments
- auto-cut visualization

## 6. Match Video Edit UI

Reason:

- Workspace UI depends on the shell model and PiP/merge stabilization.
- `Stage Composite` remains blocked until the clip persistence/read support pass closes the audited backend gap.

Closeout:

- workspace grid
- shared defaults and overrides
- Setup Once, Apply Everywhere
- batch export
- Match Recap UI
- Stage Composite UI deferred until step 9

## 7. UI Support Pass

Reason:

- The audit confirmed a small but real backend gap for truthful composite and angle-director UI.

Closeout:

- clip persistence
- stage clip read route
- angle-director plan read route
- landing page API routes
- analytics API routes
- archive API routes

## 8. Performance Library UI

Reason:

- Library browsing depends on the rest of the shell/navigation model being stable.
- Analytics depend on backend routes.

Closeout:

- summary tiles
- filter/search/sort UI
- detail and reopen UI
- analytics dashboard
- tags and notes

## 9. Stage Composite Completion

Reason:

- `Stage Composite` should only be called complete after the audited backend gap is closed.

Closeout:

- composite clip list
- clip add/update/remove UI
- camera job and audio balance UI
- override smart cuts UI
- composite render action

## 10. Export And Output Workflows

Reason:

- Export workflows depend on all editor surfaces being stable.

Closeout:

- batch export queue
- export progress
- export completion summary
- Match Recap render
- Stage Composite render

## 11. Proof, Regression, And Release

Reason:

- The new UI structure and PiP behavior need targeted proof before broader runs and any release claims.

Closeout:

- targeted UI suites
- PiP performance proof
- browser E2E
- packaged proof
- release wording checks
