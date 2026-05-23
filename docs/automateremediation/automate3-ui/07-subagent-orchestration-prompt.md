# Automate3 UI Orchestration Prompt

You are the Automate3 UI implementation agent. Build the final SplitShot browser UI to user-ready quality.

## Read Order

1. `docs/automate3/MASTER.md`
2. `docs/automate3/01-current-state-audit.md`
3. `docs/automate3/02-end-to-end-workflow-spec.md`
4. `docs/automate3/08-technical-architecture.md`
5. `docs/automate3-ui/MASTER.md`
6. `docs/automate3-ui/spec.md`
7. `docs/automate3-ui/execution-order.md`
8. `docs/automate3-ui/todo.md`
9. `docs/automate3-ui/artifacts/dom-restructure-plan.md`
10. `docs/automate3-ui/artifacts/file-change-map.md`
11. `docs/automate3-ui/artifacts/visual-design-contract.md`
12. `docs/automate3-ui/artifacts/test-preservation-contract.md`
13. all files in `docs/automate3-ui/tracks/`
14. all files in `docs/automate3-ui/artifacts/`

## Mission

Implement Landing Page, Stage Video Edit, Match Video Edit, and Performance Library as separate but integrated frontends. Preserve Stage editor functionality. Make Match and Library first-class product views. Complete all workflows, tests, docs, and visual proof.

## Required Sequence

1. Audit current UI/code/routes and regenerate screenshot artifacts.
2. Split shell/view architecture using the Wrap, Move, Hide, Retire migration.
3. Build Landing.
4. Refine Stage.
5. Stabilize PiP/waveform/multi-angle.
6. Build Match.
7. Build Library.
8. Complete export workflows.
9. Polish integration and responsive/accessibility states.
10. Run proof and update matrices.

## Completion Bar

Do not report completion until:

- every visible control is wired or intentionally disabled
- empty and loaded screenshots exist for each view
- targeted tests pass
- `tests/browser/` passes
- canonical grouped runner passes or has an external blocker
- `artifacts/readiness-gate.md` says ready with evidence.

## If You Do Not Have Vision Capability

You still own screenshot generation and mechanical proof, but you cannot self-certify visual quality.

Required:

1. Capture all required screenshots with deterministic scripts.
2. Generate a contact sheet and screenshot index.
3. Run DOM/layout assertions proving the intended view is active, required controls are visible, forbidden old chrome is absent, panels have non-zero bounds, there is no obvious overflow, and the console is clean.
4. Record all screenshot paths and assertion commands in `artifacts/ui-proof-matrix.md`.
5. Mark `artifacts/readiness-gate.md` as blocked on visual review, not ready, until a vision-capable reviewer or human confirms the screenshots.

Do not claim the app looks professional if you cannot inspect the images.
