# Agent Rules

## Before Editing

- Read `docs/automate3/MASTER.md`.
- Read `docs/automate3-ui/spec.md`.
- Read `docs/automate3-ui/artifacts/dom-restructure-plan.md`.
- Read `docs/automate3-ui/artifacts/file-change-map.md`.
- Read `docs/automate3-ui/artifacts/visual-design-contract.md`.
- Read `docs/automate3-ui/artifacts/test-preservation-contract.md`.
- Inspect current files in `src/splitshot/browser/static/`.
- Inspect relevant backend routes before wiring UI controls.
- Check git status and preserve unrelated changes.

## During Implementation

- Preserve existing Stage editor workflows.
- Do not duplicate controls.
- Do not expose the legacy rail as product-level navigation.
- Do not leave dead buttons.
- Do not call routes during every pointermove or playback frame.
- Keep `/api/state` summary-oriented.
- Use dedicated routes for heavy view data.

## Documentation And Proof

- Update `progress.md` as phases move.
- Update `artifacts/ui-gap-matrix.md` when gaps close.
- Update `artifacts/ui-proof-matrix.md` with command and screenshot evidence.
- Do not mark the package complete without screenshots and tests.

## Agents Without Vision Capability

- Capture screenshots and contact sheets, but do not claim visual polish from files you cannot inspect.
- Add DOM/layout assertions for required text, active view, absent legacy chrome, non-zero panel bounds, overflow checks, and console cleanliness.
- Leave readiness blocked on visual review until a human or vision-capable reviewer signs off.
