# Implementation Quality Contract

This document defines how the future implementation must be written, completed, verified, and reported.

## Purpose

The rest of `docs/automate` defines product, schema, route, storage, and proof targets.

This document defines the execution standard for the implementation agent so code does not land half-wired, ambiguous, or difficult to maintain.

## Code Clarity Rules

The implementation must:

- preserve the current SplitShot architecture unless a documented contract in this package requires expansion
- prefer minimal diffs that extend existing seams instead of building a second parallel system
- keep `Project` as the authoritative stage-truth model
- keep SplitShot-native names consistent across:
  - types
  - route names
  - state keys
  - UI labels
  - release notes
- avoid duplicate truth holders for:
  - stage timing
  - stage scoring
  - output profile ownership
  - library reopen targets
- add inline comments only where logic is not obvious from structure alone
- keep persistence, controller, browser-state, and export responsibilities separate

The implementation must not:

- create a second stage-truth schema beside `Project`
- copy competitor naming into code or tests
- introduce route families without matching persistence/state/controller ownership
- mark a UI capability complete if it is still mocked, local-only, or not persisted

## Code Completion Rules

No capability is complete until every required layer is present.

For each delivered capability, completion means:

1. model exists
2. persistence exists
3. controller orchestration exists
4. browser route/state contract exists
5. UI behavior exists
6. targeted tests exist
7. E2E or packaged proof exists when the feature is user-visible

Partial delivery is not allowed in these forms:

- route exists without persistence
- UI exists without route/state wiring
- persistence exists without browser/API reachability
- proof exists only for source-level helpers while visible flows remain untested
- docs claim parity or completion while the packaged flow is unproven

## Definition Of Done By Capability Class

### Schema or persistence capability

Done only when:

- disk layout is implemented
- compatibility behavior is implemented
- save/load round-trip tests pass
- regression coverage for legacy stage bundles passes

### Browser/API capability

Done only when:

- route payload contract is implemented
- state serialization is updated
- controller writes are durable
- route failure behavior is tested

### Export capability

Done only when:

- output profile fields resolve into real export behavior
- the exported artifact can be rendered from authoritative truth
- retained review-video behavior is correct when applicable

### Library capability

Done only when:

- records are written from accepted save points
- query surfaces can retrieve the records
- reopen targets resolve deterministically
- stale proxy behavior is proven

### Packaged capability

Done only when:

- the packaged app exercises the flow successfully
- no host-only dependency is required
- no local-only fixture assumption remains

## Regression Discipline

Every phase must define its regression blast radius before code changes begin.

The implementation agent must identify:

- which legacy routes must remain unchanged
- which saved-bundle behaviors must remain unchanged
- which packaged flows were already proven and must stay green
- which visible browser behaviors are frozen user-facing contracts

Regression proof order:

1. targeted tests for the touched contract
2. relevant suite for the touched subsystem
3. browser or audit slice when the UI contract changed
4. canonical grouped runner only after the narrower proof is green

No broad reruns should replace missing targeted proof.

## Evidence And Reporting Rules

When reporting proof, use:

- command run
- pass/fail
- failing test names only when red
- key error line only when needed
- artifact path for long output

Do not claim:

- `done`
- `complete`
- `parity achieved`
- `no regressions`

without matching proof in [10-acceptance-and-proof.md](10-acceptance-and-proof.md).

## Release-Readiness Link

Any capability marked complete under this contract must also satisfy [11-release-readiness.md](11-release-readiness.md) before it can be described as shippable.

## Acceptance Rule

The implementation agent should be able to pick any capability in this package and know:

- which layers must be changed
- what clean code looks like in this repo
- what counts as complete
- what proof must exist before the feature can be called done
