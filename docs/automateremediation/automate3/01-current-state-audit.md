# Current State Audit

The Automate3 plan references a 2026-05-21 UI audit, but screenshot artifacts are not guaranteed in repo truth. They may exist in a local workspace or previous run output, but Phase 0 must generate them before implementation starts.

## Required Phase 0 Evidence

Generate or refresh these artifacts before implementation:

- SplitShot contact sheet: `artifacts/ui-audit-2026-05-21/contact-sheet.png`
- Shotcut reference sheet, if reference images are available: `artifacts/ui-audit-2026-05-21/shotcut-reference-sheet.png`
- Surface captures:
  - `artifacts/ui-audit-2026-05-21/fresh-00-landing.png`
  - `artifacts/ui-audit-2026-05-21/fresh-01-single-surface.png`
  - `artifacts/ui-audit-2026-05-21/fresh-02-match-surface.png`
  - `artifacts/ui-audit-2026-05-21/fresh-03-performance-library.png`
  - `artifacts/ui-audit-2026-05-21/fresh-single-pane-*.png`

If any file is missing, the agent must record that in `docs/automate3-ui/artifacts/current-screenshot-audit.md` and regenerate it.

## Findings

The current UI is not acceptable as the final Automate UI. Phase 0 screenshots must confirm or update these findings:

- surfaces are not true separate views
- the automation strip is bolted onto the editor
- Match Video Edit inherits editor chrome and feels like a panel, not a workspace
- Performance Library inherits editor chrome and feels like a utility panel, not the app's historical record
- visual hierarchy is weak
- navigation layers compete
- empty states look unfinished
- current screenshot evidence must not be accepted as final proof until regenerated for the active implementation branch
- the landing page exists but is not enough to compensate for the view model failure
- Stage Video Edit has useful editor foundation but needs simplification, grouping, and integrated output/multi-angle workflows.

## Consequence

Automate3 must not continue patching the current shape as-is. It must split the frontend into distinct view layouts while preserving shared state, backend routes, and Stage editor capabilities.
