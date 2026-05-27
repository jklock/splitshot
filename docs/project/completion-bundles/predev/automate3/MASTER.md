> **Note:** Current status: implementation in progress. See `14-truth-audit-matrix.md` for live status.


# MASTER

`docs/automate3/` is the product, backend, data, workflow, proof, and release truth source for the final SplitShot UI remediation. `docs/automate3-ui/spec.md` is the browser-shell implementation authority.

## Product Model

SplitShot is a professional, local-first, analysis-first competition shooting video editor. It is not a generic video maker. The product has four frontend views:

- **Landing Page**: front door, recent work, quick starts, and clean entry into the app.
- **Stage Video Edit**: deep single-stage editor. It preserves the current editor foundation while simplifying and grouping it into a professional workspace.
- **Match Video Edit**: first-class match/workspace editor with stage grid, shared defaults, stage overrides, recap, composite, batch export, and Setup Once Apply Everywhere.
- **Performance Library**: canonical historical record with analytics, retained proxies, notes, tags, comparison, export, and reopen actions.

## Non-Negotiables

1. The views must be distinct frontends, not one global cockpit with panels hidden and shown.
2. The app must stay integrated: Stage, Match, and Library share state and history, but navigation never hijacks the user.
3. Stage Video Edit keeps the existing deep editor capabilities.
4. Match Video Edit and Performance Library must feel like first-class destinations.
5. Shotcut is a professional quality and information-architecture reference, not a visual clone target.
6. `/api/state` stays summary-oriented; view-specific heavy data uses dedicated routes.
7. No surface is complete without empty-state and loaded-state screenshots.
8. No user-facing claim is complete without tests and visual proof.
9. Do not modify `flutter_app/`. It is isolated to its own branch/worktree and must be treated as ignored branch-local work on `main`.
10. Outside the Landing Page, visible UI chrome must not use emoji. Stage, Match, Library, and the shell use SplitShot-native text, badges, or existing icon assets.
11. Match Video Edit and Performance Library must use the full available application viewport and must not include oversized top title bars.

## Done Means

Done means user-ready:

- app launches cleanly
- every view has a coherent layout
- every visible control is wired or explicitly unavailable with a clear reason
- Stage, Match, and Library transitions preserve context
- exports and library history work
- targeted tests, `tests/browser/`, and the canonical grouped runner pass or have documented external blockers
- final screenshots prove the UI looks like the intended product.
