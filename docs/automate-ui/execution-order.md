# Execution Order

This is the same-day dependency order for completing the UI overhaul.

## 1. PiP Performance And Merge Editor

Reason:

- The current PiP preview is too jumpy to sync visually.
- If preview playback is not trustworthy, merge and Stage Composite UI work is blocked by a broken interaction foundation.

Closeout:

- smooth preview playback
- bounded drift correction
- reseek only on defined boundaries
- drag without heavy render/sync churn

## 2. Shell Navigation And Surface Model

Reason:

- The shell still presents the old flat tool rail.
- The rest of the UI needs correct top-level surface framing before pane-specific work lands.

Closeout:

- top-level surface switcher
- context header
- mode-aware pane model

## 3. Single Video UI

Reason:

- Existing stage-edit panes already exist and can be reorganized and extended first.
- Output profiles are the clearest visible gap between backend completion and user usability.

Closeout:

- output-profile manager
- stage output configuration UI
- render-plan and retained-review source UX

## 4. Multi Video UI

Reason:

- Workspace and stage-composite UI depend on the shell model and PiP/merge stabilization.

Closeout:

- workspace grid
- shared defaults and overrides
- Match Recap UI
- Stage Composite UI

## 5. Performance Library UI

Reason:

- Library browsing depends on the rest of the shell/navigation model being stable.

Closeout:

- summary tiles
- filter/search/sort UI
- detail and reopen UI

## 6. UI Support Pass

Reason:

- The UI needs a few read/persistence deltas to avoid fake or incomplete surfaces.

Closeout:

- clip persistence
- stage clip read route
- angle-director plan read route

## 7. Proof, Regression, And Release

Reason:

- The new UI structure and PiP behavior need targeted proof before broader runs and any release claims.

Closeout:

- targeted UI suites
- PiP performance proof
- browser E2E
- packaged proof
- release wording checks
