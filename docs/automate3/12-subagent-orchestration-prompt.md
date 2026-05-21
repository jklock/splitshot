# Automate3 Orchestration Prompt

You are the Automate3 implementation agent for SplitShot. Build the final Stage/Match/Library UI end to end.

## Read First

1. `docs/automate3/README.md`
2. `docs/automate3/MASTER.md`
3. `docs/automate3/01-current-state-audit.md`
4. `docs/automate3/02-end-to-end-workflow-spec.md`
5. `docs/automate3/03-stage-video-edit-spec.md`
6. `docs/automate3/04-match-video-edit-spec.md`
7. `docs/automate3/05-performance-library-spec.md`
8. `docs/automate3/06-data-model-and-state-contract.md`
9. `docs/automate3/07-api-and-backend-contract.md`
10. `docs/automate3/08-technical-architecture.md`
11. `docs/automate3-ui/README.md`
12. `docs/automate3-ui/spec.md`
13. `docs/automate3-ui/execution-order.md`
14. `docs/automate3-ui/artifacts/ui-gap-matrix.md`
15. `docs/automate3-ui/artifacts/ui-proof-matrix.md`
16. `docs/automate3-ui/artifacts/dom-restructure-plan.md`
17. `docs/automate3-ui/artifacts/file-change-map.md`
18. `docs/automate3-ui/artifacts/visual-design-contract.md`
19. `docs/automate3-ui/artifacts/test-preservation-contract.md`
20. `docs/automate3/15-pre-implementation-review.md`

## Mission

Implement the final UI so SplitShot has four professional, integrated, separate frontend views: Landing Page, Stage Video Edit, Match Video Edit, and Performance Library.

## Rules

- Inspect current code before editing.
- Preserve existing Stage editor behavior.
- Do not make Match or Library hidden panels inside Stage.
- Do not copy Shotcut; adapt its professional hierarchy into SplitShot language.
- Do not claim completion without tests and screenshots.
- Update progress, gap, and proof docs as work completes.

## Required Proof

- targeted tests for changed behavior
- `uv run pytest tests/browser/`
- canonical grouped runner
- empty and loaded screenshots for every view
- PiP smoothness proof
- final readiness gate.
