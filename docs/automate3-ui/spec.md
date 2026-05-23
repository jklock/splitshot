> **Note:** Current implementation is partial; see `14-truth-audit-matrix.md` for actual status.


# Automate3 UI Spec

## Goal

Build the final SplitShot browser UI as four professional, integrated, separate frontend views:

- Landing Page
- Stage Video Edit
- Match Video Edit
- Performance Library

The result must be fully functional, visually proven, tested, and ready for users.

## Shared Shell

The shell owns:

- app logo and Home behavior
- active view switcher
- global context: project, match, stage, output/proxy/export status
- global notifications
- route/view error boundary
- settings access
- responsive frame.

The shell must not own a permanent automation strip. View-specific controls live inside their owning view.

For exact DOM structure, see `artifacts/dom-restructure-plan.md`. For visual tokens, see `artifacts/visual-design-contract.md`.

Visible emoji are allowed only on the Landing Page. Stage, Match, Library, shell navigation, tool rails, status controls, setup prompts, and workflow buttons must use text labels, existing icon assets, or styled badges instead of emoji.

## Landing Page

Required:

- first-run and returning-user states
- three entry cards
- recent stages from `/api/landing/recent`; current backend returns stage project directories only, so the recent activity section should be titled "Recent Stages" and must not reserve space for Match/Library records until backend support exists
- quick starts: New Stage, New Match, Open File
- help/settings/version access
- professional dark visual treatment
- responsive layout.

## Stage Video Edit

Required:

- preserve current editor panes inside Stage
- simplify and group tool navigation
- preview/timeline/inspector hierarchy
- no-media empty state
- loaded media state
- workspace-stage state
- output profile CRUD
- retained review source
- render-plan preview and render result
- PiP/multi-angle controls
- waveform enhancements
- create/attach Match from Stage without forced navigation
- return to Match when opened from Match.

## Match Video Edit

Required:

- match header and save/export actions
- stage grid with thumbnails/statuses/badges/actions
- drag reorder
- shared defaults
- stage overrides
- Setup Once Apply Everywhere preview/apply
- PractiScore import/status
- Match Recap builder
- Stage Composite builder
- batch export queue and progress
- clean open Stage / return behavior.
- full-viewport workspace layout with no centered max-width cap
- no oversized view title bar; keep New/Save/Export controls in a compact action bar or in the relevant panel.

## Performance Library

Required:

- dashboard summary tiles
- search/filter/sort
- record table
- selected detail
- proxy/archive state and actions
- analytics charts
- personal bests
- outliers
- discipline breakdown
- comparison
- tags and notes
- CSV/JSON export
- reopen Stage/Match actions
- automatic history updates from Stage/Match completion without navigation.
- full-viewport workspace layout with no centered max-width cap
- no oversized view title bar; keep refresh/export controls in a compact action bar or in the relevant panel.

## PiP, Waveform, Multi-Angle

Required:

- bounded rate correction for small drift
- hard seek only on defined boundaries or large drift
- drag updates are local and RAF-driven
- route commit only on pointerup/debounced settle
- multi-track waveform
- color-coded segments
- auto-cut visualization
- camera jobs
- audio balance
- smart cuts and overrides
- line-up angles.

## Empty, Loading, Error, Responsive

Every view must define:

- empty state
- loading state
- route error state
- partial/stale state where applicable
- unavailable action state
- narrow viewport behavior
- keyboard/focus behavior

For exact copy, visual treatment, and actions for each state, see `tracks/09-empty-loading-error-and-responsive-states.md`.

## Proof

No view is complete without:

- targeted tests
- browser E2E for core flow
- empty screenshot
- loaded screenshot
- proof matrix entry
- no false completion language.

If the implementation agent has no vision capability, it must also produce a screenshot index, contact sheet, DOM/layout assertion report, and an explicit readiness blocker for external visual review. It must not self-certify that the UI looks correct.
