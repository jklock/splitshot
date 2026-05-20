# Subagent Orchestration Prompt

Use this prompt verbatim or with only minimal task-wrapper changes when assigning the full `docs/automate` implementation to another agent.

## Prompt

You are implementing the SplitShot automation package defined in `docs/automate/`.

Your job is to complete the full feature set described there with no product, naming, schema, route, storage, proof, parity, or release ambiguity left unresolved in code.

You must follow the repo instructions in `AGENTS.md` and the full `docs/automate` package. Treat the docs package as the implementation contract.

## Read Order

Before changing code, read these documents in this order:

1. `docs/automate/00-product-definition.md`
2. `docs/automate/00a-splitshot-naming-contract.md`
3. `docs/automate/00b-implementation-quality-contract.md`
4. `docs/automate/01-shootingcut-feature-matrix.md`
5. `docs/automate/02-editor-workflow-spec.md`
6. `docs/automate/03-performance-library-spec.md`
7. `docs/automate/04-data-model-spec.md`
8. `docs/automate/05-technical-architecture.md`
9. `docs/automate/06-feature-spec-single-video.md`
10. `docs/automate/07-feature-spec-multi-video.md`
11. `docs/automate/08-feature-spec-performance-library.md`
12. `docs/automate/09-roadmap-and-task-plan.md`
13. `docs/automate/10-acceptance-and-proof.md`
14. `docs/automate/11-release-readiness.md`

Do not begin implementation until you understand:

- `main` on `v1.0.5` is the regression floor for all continuing work
- `Project` remains the stage-truth model
- `Match Recap` and `Stage Composite` are separate first-delivery flows
- parity is outcome-based only
- packaged proof is mandatory for release claims
- no copied competitor names are allowed in implementation-facing surfaces

## Non-Negotiable Rules

You must:

- preserve the shipped `v1.0.5` Windows export-font, OCR-proof, and packaged-fixture baseline
- preserve the current SplitShot architecture and extend existing seams
- keep `Project` as the authoritative stage-truth model
- add additive workspace/library/proxy systems instead of replacing legacy single-stage behavior
- use SplitShot-native naming only
- keep legacy `project.json` open/save behavior working
- wire every delivered capability through model, persistence, controller, route/state, UI, and proof
- prove user-visible work with targeted tests first, then relevant suites, then broader browser or packaged proof
- update release-facing artifacts when the shipped feature set changes

You must not:

- introduce a parallel stage-truth schema
- copy Shot Cut naming into routes, types, tests, UI labels, changelog entries, or release notes
- leave partial route families, stub UI, or unpersisted behavior and call it complete
- claim parity, completion, release-readiness, or no regressions without proof

## Execution Order

Implement in the phase order defined by `docs/automate/09-roadmap-and-task-plan.md`.

Follow this sequence exactly:

1. Product and data-model foundation
2. Seamless Single/Multi editor model
3. Performance Library foundation
4. Retained proxy generation and recall
5. Single Video features
6. Multi Video features
7. Final integration and packaged proof

Do not reorder phases for convenience unless a concrete repo fact proves a different order is required. If that happens, document the reason and keep the dependency chain explicit.

## Required Implementation Outcomes

### Foundation

Implement:

- stage/workspace/library/proxy models
- stable ids and relationships
- disk layout and compatibility behavior
- persistence modules for workspaces and library records
- migration-safe handling for legacy single-stage bundles

### Editor scope

Implement:

- workspace CRUD
- stage membership and ordering
- stage open from workspace and return to workspace
- shared defaults and stage overrides
- browser-state scope and inheritance surfaces

### Output system

Implement:

- stage and match `output_profile` support
- `Run Window`
- `Metric Captions`
- `Frame Profiles`
- `Lead-In Card`
- `Brand Mark`
- persisted `Subject Track Crop` hooks

### Multi Video flows

Implement separately:

- `Match Recap`
- `Stage Composite`
- `Angle Align`
- `Angle Director`
- `Angle Roles`
- `Audio Mix Lanes`
- `Result Cards`

Treat `Match Recap` and `Stage Composite` as separate schemas, separate route/state surfaces, separate UI flows, and separate proof targets.

### Performance Library

Implement:

- stage and match library records
- normalized metric indexes
- retained proxy records
- history query and browse flows
- reopen-to-editor flows
- proxy refresh and stale detection

## Required Code Areas

Expect to touch, at minimum:

- domain models
- persistence layers
- controller orchestration
- browser state serialization
- browser server routes
- browser static UI
- export pipeline
- tests
- release-facing docs/artifacts if the work is shipping

Prefer extending current files and patterns before creating new subsystems.

## Testing And Proof Order

Use the proof rules from `docs/automate/10-acceptance-and-proof.md`.

Minimum order:

1. targeted contract tests
2. relevant suite
3. browser or packaged audit slice when visible behavior changed
4. canonical grouped runner only after narrower proof is green

Use the documented command matrix, including:

- `uv run pytest tests/persistence/test_persistence.py`
- `uv run pytest tests/persistence/test_project_lifecycle_contracts.py`
- `uv run pytest tests/browser/test_browser_control.py`
- `uv run pytest tests/browser/test_project_lifecycle_contracts.py`
- `uv run pytest tests/browser/test_settings_defaults_truth_gate.py`
- `uv run pytest tests/browser/test_merge_export_contracts.py`
- `uv run pytest tests/export/test_export.py`
- `uv run pytest tests/export/test_merge_export_contracts.py`
- `uv run pytest tests/browser/test_browser_full_app_e2e.py`
- `uv run pytest tests/browser/test_browser_remaining_controls_e2e.py`
- `uv run pytest tests/browser/test_metrics_e2e.py`
- `uv run python scripts/audits/browser/run_browser_interaction_audit.py`
- `uv run python scripts/audits/browser/run_browser_ui_surface_audit.py`
- `uv run python scripts/audits/browser/run_browser_export_matrix.py`
- `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`

When packaged flows are in scope, use the packaged backend with the supported audit targeting flow and prove:

- stage outputs
- `Match Recap`
- `Stage Composite`
- retained proxy generation
- library browse and reopen

## Regression Requirements

Before and after each phase, identify the regression blast radius and protect:

- the shipped `v1.0.5` Windows export-font and OCR proof path
- packaged `docs/Clip1.MP4` fixture validation
- legacy single-stage `project.json` behavior
- existing `/api/project/*` semantics
- existing export behavior for stage-only flows
- previously proven packaged launch and interaction flows

Do not use a broad suite run as a substitute for targeted regression proof.

To claim no known regressions against frozen visible contracts, provide:

- targeted proof
- relevant-suite proof
- visible-flow browser or packaged proof
- any remaining risk for unrun broader checks

## Release Requirements

If the work is shippable in the branch you are producing, also satisfy `docs/automate/11-release-readiness.md`.

That means:

- version-source updates if a release is actually being cut
- `CHANGELOG.md` updates with SplitShot-native names
- generated release notes aligned to the shipped outcomes
- live GitHub release body updated if the release already exists and is stale
- no packaged-release claims without packaged proof

Do not restate competitor names in changelog or release notes.

## Reporting Format

At the end of each meaningful work segment, report:

- what changed
- what was verified
- exact commands run
- pass/fail
- failing test names only if red
- artifact paths for long output
- remaining risks

Do not report vague completion. Tie every claim to proof.

## Final Acceptance Standard

The work is complete only when all of the following are true:

- every implemented capability matches the docs package contract
- all implementation-facing names are SplitShot-native
- every delivered capability is fully wired through all required layers
- the E2E scenarios in `10-acceptance-and-proof.md` are satisfied
- packaged proof exists for the shipped visible flows
- release-readiness rules are satisfied if the work is being shipped
- parity claims are backed by outcome proof, not naming similarity

If any part of the package cannot be completed, stop calling it complete and report the blocker precisely.
