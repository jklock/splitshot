# Acceptance and Proof

This document defines the proof standard for the automation plan set.

## Proof Rule

Do not claim completion from design docs, source-only success, or partial browser smoke.

The final implementation must prove:

- shipped `v1.0.5` baseline preservation
- source truth correctness
- editor-scope correctness
- persistence correctness
- export correctness
- library/history correctness
- packaged-app parity

## Source-level Tests

Need targeted tests for:

- data model additions
- inheritance resolution
- output variant schema
- library record updates
- proxy invalidation and refresh rules

## Browser Tests

Need targeted browser truth gates for:

- Single to Multi transitions
- inherited vs overridden field behavior
- stage opening from Multi
- library browsing and jump-to-editor flows
- output variant creation and selection

## Export Tests

Need export truth gates for:

- Single Video output variants
- Multi Video shared output recipes
- Lead-In Card
- Brand Mark
- ratio-aware outputs
- later Subject Track Crop behavior
- retained review proxy generation

## Persistence Tests

Need persistence coverage for:

- stage records
- match workspaces
- shared defaults
- stage overrides
- output variants
- library records
- retained proxy metadata

## Library and History Tests

Need explicit tests for:

- historical metric indexing
- cross-match comparisons
- linked run resolution
- proxy playback availability
- jump from library to editor

## Packaged-app E2E

Packaged proof must cover:

- preservation of the `v1.0.5` Windows export-font and OCR proof path
- built-artifact execution on supported desktop platforms
- library record creation and playback
- retained proxy generation
- stage and match export flows
- no dependency on host-installed tools for packaged behavior
- no dependency on local-only fixtures

## Main Baseline Regression Shield

Before calling any automation work complete, re-prove that the merged `main` baseline still holds:

- overlay exports on Windows still use the `font_policy.py` family rules
- browser preview font stacks still align to the Windows-safe release defaults
- packaged CI and release workflows still validate `docs/Clip1.MP4`
- packaged Windows proof still includes OCR readability checks
- previously shipped single-stage browser/export flows still pass their owning targeted tests

## Final Parity Audit

Before calling the work complete:

- re-run the Shooting Cut matrix
- classify each competitor feature as:
  - done
  - partial
  - deferred
  - rejected by design
- prove every `done` claim with an owning test or packaged artifact flow

## Minimum Acceptance Scenarios

- Open a stage in Single Video, review it, create multiple outputs, and persist them.
- Open a match in Multi Video, apply shared settings, override one stage, and verify sibling stages remain inherited.
- Compare one metric over time in Performance Library and open the associated retained review video.
- Jump from a library record into the correct editor context.
- Validate all of the above in packaged desktop builds.

## Capability Proof Matrix

| Capability | Source of truth doc | Data model impact | Route/state impact | Required tests | Packaged proof |
| --- | --- | --- | --- | --- | --- |
| Legacy single-stage open/save | `04-data-model-spec.md` | preserve `Project` and `project.json` | existing `/api/project/open` and `/api/project/save` continue to work | persistence compatibility test | open bundled stage project in packaged app |
| Single to Multi stage identity preservation | `02-editor-workflow-spec.md` | stable `stage_id` linkage | `/api/workspace/stage/open`, `/api/workspace/stage/return`, `/api/state.editor_scope` | browser navigation test | open stage from workspace and return in packaged app |
| Match shared defaults and stage overrides | `02-editor-workflow-spec.md`, `04-data-model-spec.md` | `workspace.json.shared_defaults`, `override_values` | `/api/workspace/defaults`, `/api/workspace/stage/override`, `/api/workspace/stage/override/reset` | inheritance resolution and browser tests | save workspace defaults in packaged app |
| Stage output profile CRUD | `06-feature-spec-single-video.md` | `OutputProfile` records on stage scope | `/api/output-profiles/*`, `/api/state.output_profiles` | route and persistence tests | create/edit/delete output profile in packaged app |
| Run Window render | `06-feature-spec-single-video.md` | output-profile-local trim fields | `/api/output-profiles/render` | export render test | render one stage output with reviewed window |
| Metric Caption render | `06-feature-spec-single-video.md` | caption preset metadata | `/api/output-profiles/render` | export truth test | play rendered stage output in packaged app |
| Match Recap render | `07-feature-spec-multi-video.md` | match-scope output profile | `/api/output-profiles/render` with `scope_type=match` | export and workspace tests | render many-stage recap in packaged app |
| Stage Composite render | `07-feature-spec-multi-video.md` | stage clip-source composition metadata | `/api/workspace/stage/clip/*`, `/api/output-profiles/render` | export and route tests | render same-stage multi-clip output in packaged app |
| Angle Align persistence | `07-feature-spec-multi-video.md` | clip-source sync metadata | workspace clip update routes and `/api/state` merge summaries | persistence and browser tests | reopen aligned stage composite in packaged app |
| Library record creation and browsing | `03-performance-library-spec.md`, `08-feature-spec-performance-library.md` | library records and metric indexes | `/api/library/list`, `/api/library/filter`, `/api/state.library_summary` | library persistence and query tests | browse history in packaged app |
| Retained review-video invalidation and refresh | `03-performance-library-spec.md`, `04-data-model-spec.md` | `RetainedProxyRecord`, truth hash | `/api/proxy/status`, `/api/proxy/refresh`, `/api/library/proxy/open` | proxy stale detection tests | regenerate and open proxy in packaged app |
| Library jump to editor | `03-performance-library-spec.md` | deterministic editor targets | `/api/library/stage/open`, `/api/library/match/open` | browser navigation tests | reopen stage and match from library in packaged app |

## Required Command And Artifact Discipline

- Start with targeted tests for touched contracts.
- Move to the relevant suite only after targeted proof passes.
- Run packaged proof only after source, persistence, and browser contracts are already validated.
- Final parity audit must link each `done` claim to one line in the matrix above.

## E2E Scenarios

### Single Video reviewed-output flow

Required scenario:

1. open or create one stage project
2. import primary media
3. confirm or adjust reviewed timing truth
4. create multiple stage output profiles
5. render at least one profile with `Run Window`
6. render at least one profile with `Metric Captions`
7. mark or derive the retained review-video source
8. confirm retained proxy creation

### Multi Video shared-default and Match Recap flow

Required scenario:

1. create one match workspace
2. add multiple stage records
3. apply shared defaults
4. override one stage only
5. verify sibling stages remain inherited
6. render one `Match Recap`

### Stage Composite and Angle Align flow

Required scenario:

1. open one workspace stage with multiple clips
2. assign angle roles
3. align same-stage sources with `Angle Align`
4. adjust clip-local audio contribution
5. render one `Stage Composite`

### Performance Library browse and reopen flow

Required scenario:

1. save accepted stage and workspace truth
2. confirm library record creation
3. query history by at least one metric or filter
4. open retained review video
5. jump back into the correct editor target

### Packaged-app critical flow

Required scenario:

1. launch the packaged app
2. run one stage output flow
3. run one workspace recap or composite flow
4. confirm retained proxy generation
5. browse and reopen from the library

## Regression Shield

### Targeted-first proof map

- domain and persistence changes:
  - targeted persistence and model tests first
- browser route and state changes:
  - targeted browser control/state tests first
- export changes:
  - targeted export tests first
- library changes:
  - targeted library persistence/query tests first
- packaged-flow changes:
  - packaged scenario proof only after the source-level slices are green

### Widening order

1. targeted contract tests
2. relevant suite
   - browser changes: `uv run pytest tests/browser/`
   - export changes: targeted export slice, then broader relevant suite
   - persistence/model changes: targeted persistence/model slice
3. browser or packaged audit slice when user-visible behavior changed
4. canonical grouped runner:
   - `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`

### No-regressions proof rule

To claim no known regressions against frozen visible contracts, the evidence must include:

- targeted tests for changed contracts
- relevant suite coverage for the touched subsystem
- packaged or browser proof for any changed visible flow
- explicit note of any unrun broader check and why it was skipped

## Command Matrix

Use the narrowest useful command first.

### Model and persistence proof

- targeted persistence:
  - `uv run pytest tests/persistence/test_persistence.py`
- project lifecycle compatibility:
  - `uv run pytest tests/persistence/test_project_lifecycle_contracts.py`

### Browser contract proof

- browser control and route coverage:
  - `uv run pytest tests/browser/test_browser_control.py`
- project lifecycle browser coverage:
  - `uv run pytest tests/browser/test_project_lifecycle_contracts.py`
- settings and inheritance coverage:
  - `uv run pytest tests/browser/test_settings_defaults_truth_gate.py`
- merge and output browser coverage:
  - `uv run pytest tests/browser/test_merge_export_contracts.py`

### Export proof

- stage and output export coverage:
  - `uv run pytest tests/export/test_export.py`
- merge/export contract coverage:
  - `uv run pytest tests/export/test_merge_export_contracts.py`

### Browser E2E and app E2E proof

- broader browser flow coverage:
  - `uv run pytest tests/browser/test_browser_full_app_e2e.py`
- remaining browser E2E coverage:
  - `uv run pytest tests/browser/test_browser_remaining_controls_e2e.py`
- metrics/browser E2E slice:
  - `uv run pytest tests/browser/test_metrics_e2e.py`

### Browser audit and packaged-flow proof

- interaction audit:
  - `uv run python scripts/audits/browser/run_browser_interaction_audit.py`
- UI surface audit:
  - `uv run python scripts/audits/browser/run_browser_ui_surface_audit.py`
- export matrix audit:
  - `uv run python scripts/audits/browser/run_browser_export_matrix.py`

When validating packaged builds, use the same audit scripts against the packaged backend with its supported `--base-url` flow.

### Final grouped runner

- canonical grouped runner:
  - `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`

## Evidence Format

Every proof report derived from this package must include:

- `Command:`
- `Result:` pass or fail
- `Failing tests:` failing test names only when red
- `Key line:` one relevant error line when needed
- `Artifact:` path to saved output when long output exists

Example shape:

- `Command: uv run pytest tests/browser/test_browser_control.py -k workspace`
- `Result: PASS`
- `Artifact: artifacts/browser-workspace-proof.txt`

## Release-Proof Link

The final proof package for shipped work must satisfy both:

- this document
- [11-release-readiness.md](11-release-readiness.md)

## Completion Rule

The implementation is not complete until all of the following are true:

- every adopted capability has a SplitShot-native implementation label
- every new persisted concept has a defined storage location
- every new route has defined payload and failure behavior
- legacy single-stage compatibility is proven
- both `Match Recap` and `Stage Composite` are proven as separate workflows
- library and retained review-video behavior are proven in packaged builds
