# Testing Specification

## Normative statement

`testing/` is Work Effort 2 / Set 2 for the SplitShot completion program.

It is the testing, proof-packaging, artifact, QA/doc-sync, and signoff overlay across the source bundles. It is not the same thing as the source `predev/tests/` bundle, which remains the detailed lane for `TST-*` work.

## Work-effort boundary requirements

### Included source scope

`testing/` must aggregate the following source-bundle scope:

- Stage `STG-007` and `STG-008`
- Match proof/signoff work tied to `MCH-002`, `MCH-003`, `MCH-004`, `MCH-006`, and all of `MCH-007`
- Performance proof/signoff work tied to `PRF-002`, `PRF-003`, `PRF-004`, `PRF-006`, and all of `PRF-007`
- Backend `BEK-007` and `BEK-008`
- Modularization `MOD-006` and `MOD-007`
- all source `predev/tests/` bundle work: `TST-001` through `TST-009`
- screenshots, artifacts, QA sync, coverage sync, test-guide sync, final suite runs, and visual approval required to close source-bundle gates

### Excluded scope

`testing/` must not silently absorb new first-order implementation work that belongs in `development/`.

If testing reveals a real implementation blocker:

- reopen the relevant source bundle explicitly,
- record the blocker in the touched ledger,
- and hand that blocker back to `development/` instead of pretending testing owned it all along.

## Aggregate `testing/` versus source `predev/tests/` requirements

- Aggregate `testing/` is the Work Effort 2 overlay for the whole program.
- Source `predev/tests/` is the detailed lane that owns `TST-001` through `TST-009`.
- The source `predev/tests/` bundle must execute inside Work Effort 2, but it must not be treated as a synonym for the aggregate `testing/` bundle.
- Docs in this directory must keep `predev/tests/` and `testing/` distinct in wording and ownership.

## Evidence requirements

`testing/` must not claim completion without acceptance-valid evidence.

Acceptance-valid evidence includes:

- focused test evidence recorded in the owning source bundle
- screenshot and DOM evidence where browser-visible bundles require it
- output artifacts where export/backup/recap workflows require them
- QA/coverage/test-guide docs synced to the final delivered behavior
- final gate closure recorded in the owning source `outcome.md`

Historical-only evidence does not count unless the owning source bundle explicitly says it still applies.

## Source-bundle final-gate requirements

`testing/` is not successful unless the relevant source final gates are also successful.

At minimum:

- Stage must close `STG-008`
- Match must close `MCH-007`
- Performance must close `PRF-007`
- Backend must close `BEK-008`
- Modularization must close `MOD-007`
- the source `predev/tests/` bundle must close `TST-009`

## Documentation and governance requirements

Any proof/signoff change that affects browser-visible behavior or suite ownership requires synchronized updates to the owning documents, including where relevant:

- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- touched source bundle `outcome.md` and `artifacts.md` files
- `../MASTER_STATUS.md`, `README.md`, and `RECOVERY_NEXT_STEPS.md` when aggregate status meaning changes

## Runner and closeout requirements

At minimum, Work Effort 2 must record:

- narrow proof runs for open source-bundle gaps
- owned suite runs where the source bundle requires them
- the canonical full-suite anchor
- visual approvals where browser-visible signoff is required
- residual risks and waivers for any approved exception

## Definition of specification success

The testing spec is satisfied only when the aggregate `testing/` bundle, the source bundles, the recorded evidence, and the final signoff state all describe the same completion truth for Work Effort 2 / Set 2.
