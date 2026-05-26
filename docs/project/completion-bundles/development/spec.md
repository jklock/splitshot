# Development Specification

## Normative statement

`development/` is Work Effort 1 / Set 1 for the SplitShot completion program.

It is the implementation-only overlay across the source bundles stored under `predev/`. It owns development, refactoring, route/state hardening, architecture work, and implementation-facing contract updates. It does not own final proof packaging, screenshot capture, final QA/doc sync, or signoff closure.

## Work-effort boundary requirements

### Included source scope

`development/` must aggregate the implementation side of the source bundles as follows:

- Stage: `STG-001` through `STG-006`
- Match: `MCH-001` plus the implementation side of `MCH-002` through `MCH-006`
- Performance: `PRF-001` plus the implementation side of `PRF-002` through `PRF-005`
- Backend: `BEK-001` through `BEK-006`
- Modularization: `MOD-001` through `MOD-005`

### Excluded source scope

`development/` must not claim completion of:

- Stage `STG-007` or `STG-008`
- Match proof/signoff packaging tied to `MCH-002`, `MCH-003`, `MCH-004`, `MCH-006`, or `MCH-007`
- Performance proof/signoff packaging tied to `PRF-002`, `PRF-003`, `PRF-004`, `PRF-006`, or `PRF-007`
- Backend `BEK-007` or `BEK-008`
- Modularization `MOD-006` or `MOD-007`
- any `TST-*` work from the source `predev/tests/` bundle

## Source-bundle integrity requirements

- The six source bundles under `predev/` remain the detailed task truth.
- `development/` must not contradict the source `tasks.md`, `spec.md`, `outcome.md`, or `artifacts.md` files.
- Any implementation change that moves a source bundle forward must update the touched source bundle and the aggregate `development/` bundle in the same change.
- `development/` may summarize, but it must not silently redefine, source task ownership.

## Implementation requirements

`development/` must own only work that changes or settles implementation truth, including:

- code and architecture changes
- shell/layout/runtime changes
- route/state/controller changes
- persistence and ownership refactors
- implementation-facing documentation or contract updates required to keep the delivered behavior truthful
- explicit implementation deferrals or residual risks when work is intentionally left for later

## Documentation and contract requirements

Implementation-facing documentation may be updated in `development/` when needed to keep current behavior truthful.

However, the following remain reserved for `testing/` unless the same change is merely preparing them for future closure:

- screenshot packages
- proof ledgers used for acceptance
- final artifact capture
- QA matrix closeout
- coverage-plan closeout
- final signoff language

Important distinction:

- the source `predev/tests/` bundle is the detailed lane for `TST-*` work
- aggregate `testing/` is the Work Effort 2 overlay
- they are not interchangeable

## Handoff requirements

At the end of Work Effort 1, `development/` must make it explicit that:

- implementation work is complete or explicitly deferred
- remaining work belongs to proof, artifacts, QA/doc sync, suite closure, or signoff
- `testing/` can proceed without re-litigating which implementation tasks still belong to Work Effort 1

## Validation requirements

`development/` may reference narrow validation used to unblock implementation.

But:

- narrow validation does not by itself close Work Effort 2
- broad green runs do not by themselves close source-bundle proof gates
- `development/` must not use testing-style evidence to claim signoff completion

## Definition of specification success

The development spec is satisfied only when the aggregate bundle, the source bundles, and the code-facing contract all describe the same implementation boundary for Work Effort 1 / Set 1.
