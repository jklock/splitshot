# Roadmap and Task Plan

This document sequences the implementation work required by the automation plan set.

## Phase 1: Product and data-model foundation

### Tasks

- formalize stage, match, output, library, and proxy record concepts
- define ids and relationships
- lock inheritance-capable settings model
- define canonical library update rules

### Owning subsystems

- domain models
- persistence
- controller contracts

### Acceptance gate

- data model docs are stable enough to implement without hidden product decisions

## Phase 2: Seamless Single/Multi editor model

### Tasks

- define stage opening and return flows
- implement match workspace membership model
- implement shared defaults and stage overrides
- expose inherited vs overridden UI state

### Owning subsystems

- controller
- browser state/server
- browser UI
- persistence

### Acceptance gate

- one stage can move between Single and Multi with no conversion friction

## Phase 3: Performance Library foundation

### Tasks

- build persistent library record store
- build library metric index
- build stage/match linking model
- add library read surfaces

### Owning subsystems

- persistence
- metrics/history indexing
- browser state/server
- browser UI

### Acceptance gate

- history can be browsed independently of opening editor projects

## Phase 4: Retained proxy generation and recall

### Tasks

- define proxy generation profiles
- implement retained proxy metadata
- implement stale detection and refresh
- connect library playback to retained proxies

### Owning subsystems

- export pipeline
- controller
- persistence
- library browsing UI

### Acceptance gate

- retained proxies open from library and stay aligned to latest reviewed truth

## Phase 5: Single Video parity features

### Tasks

- Run Window
- Metric Captions
- output profiles
- Lead-In Card
- Brand Mark
- Frame Profiles
- Subject Track Crop design hooks

### Owning subsystems

- Single Video UI
- export pipeline
- controller
- persistence

### Acceptance gate

- one reviewed stage can produce multiple named outputs from the same truth

## Phase 6: Multi Video parity features

### Tasks

- batch match ingest
- match-wide recipe application
- stage overrides
- Match Recap workflow
- Stage Composite workflow
- Angle Align productization
- Angle Director productization
- Angle Roles
- Audio Mix Lanes
- Result Cards

### Owning subsystems

- Multi Video UI
- controller
- export pipeline
- persistence

### Acceptance gate

- many stages in one match can be processed consistently without losing per-stage truth

## Phase 7: Final integration and packaged proof

### Tasks

- integrate library/editor/output flows
- packaged desktop proof
- retention and playback proof
- parity audit against feature matrix

### Owning subsystems

- test harnesses
- packaged workflows
- documentation and audit surfaces

### Acceptance gate

- source, browser, export, persistence, and packaged proofs all pass

## Dependency Notes

- Phase 1 must finish before the rest can be implemented safely.
- Phase 2 must precede most Multi Video work.
- Phase 3 and 4 must land before Performance Library can be trusted as canonical.
- Phase 5 and 6 can overlap once the data model and editor-scope model are stable.

## Execution-Grade Phase Gates

### Phase 1: Product and data-model foundation

Entry criteria:

- current package naming contract accepted
- live code seams reviewed against current repo

Deliverables:

- SplitShot-native naming contract
- exact stage/workspace/library/proxy schema definitions
- exact disk layout definitions
- exact compatibility rules for legacy `project.json`

Blocking dependencies:

- none

Required tests:

- serialization tests for new records
- legacy single-stage load compatibility tests

Proof before close:

- the implementation agent can create new models and persistence files without inventing ids, layouts, or migration rules
- code clarity gate:
  - no duplicate stage-truth models
  - no competitor naming in implementation-facing surfaces
- code completion gate:
  - every foundation contract has a concrete owner and no unresolved placeholders
- regression gate:
  - legacy `project.json` compatibility tests pass before moving on

### Phase 2: Seamless Single/Multi editor model

Entry criteria:

- Phase 1 schema and disk layout are locked

Deliverables:

- workspace route contract
- `/api/state` scope additions
- stage open/return behavior
- inheritance and override contract

Blocking dependencies:

- Phase 1 complete

Required tests:

- browser stage-open/return test
- override resolution test

Proof before close:

- one `stage_id` moves between `Single Video` and `Multi Video` with no duplication
- code clarity gate:
  - route names, state keys, and UI labels match the naming contract
- code completion gate:
  - workspace flow is wired through persistence, controller, route, state, and UI layers
- regression gate:
  - existing single-stage `/api/project/*` flows still pass their targeted tests

### Phase 3: Performance Library foundation

Entry criteria:

- Phase 1 ids and persistence layout locked

Deliverables:

- library record schemas
- library storage location
- library browse/filter/open route contract
- normalized metric index contract

Blocking dependencies:

- Phase 1 complete

Required tests:

- record creation tests
- query tests

Proof before close:

- history can be queried without reopening project folders
- code completion gate:
  - record write, query, and reopen targets all exist together
- regression gate:
  - stage save behavior still works without requiring the library UI

### Phase 4: Retained proxy generation and recall

Entry criteria:

- Phase 3 library record model complete
- output profile schema complete

Deliverables:

- retained review-video metadata schema
- proxy invalidation rules
- proxy refresh route contract
- playback/open contract

Blocking dependencies:

- Phase 3 complete

Required tests:

- proxy generation
- proxy stale detection
- proxy playback resolution

Proof before close:

- the current proxy is provably tied to the current accepted truth hash
- code completion gate:
  - proxy generation, status, invalidation, and playback are all wired
- regression gate:
  - existing export flows still render when proxy refresh is not requested

### Phase 5: Single Video parity features

Entry criteria:

- Phase 1 and 2 complete

Deliverables:

- `Run Window`
- `Metric Captions`
- stage `Output Profiles`
- `Frame Profiles`
- `Lead-In Card`
- `Brand Mark`
- persisted `Subject Track Crop` hooks

Blocking dependencies:

- output profile schema
- stage route/state support

Required tests:

- stage output profile CRUD
- stage render tests

Proof before close:

- one reviewed stage can produce multiple named outputs without duplicating truth
- code clarity gate:
  - output-profile code does not fork stage truth
- code completion gate:
  - profile model, persistence, route, state, UI, and export proof all exist
- regression gate:
  - legacy single-stage export behavior stays green
- parity gate:
  - shipped adopted outcomes are mapped to SplitShot-native proof entries
- release gate:
  - [11-release-readiness.md](11-release-readiness.md) checklist is satisfiable for the shipped stage capabilities

### Phase 6: Multi Video parity features

Entry criteria:

- Phase 1 and 2 complete

Deliverables:

- workspace stage membership flows
- shared defaults and overrides
- `Match Recap`
- `Stage Composite`
- `Angle Align`
- `Angle Director`
- `Angle Roles`
- `Audio Mix Lanes`
- `Result Cards`

Blocking dependencies:

- workspace persistence and routing

Required tests:

- workspace lifecycle tests
- recap render tests
- stage composite render tests

Proof before close:

- both multi-stage and same-stage-many-clip outputs work as separate documented flows
- code clarity gate:
  - recap and composite flows remain separate in schema, routes, and proof
- code completion gate:
  - shared defaults, overrides, angle state, audio state, and result-card state are all wired
- regression gate:
  - pre-existing merge/PiP single-stage behavior does not silently break
- parity gate:
  - adopted multi-angle outcomes have explicit proof owners
- release gate:
  - packaged proof exists for recap and composite flows before they are considered shippable

### Phase 7: Final integration and packaged proof

Entry criteria:

- phases 1 through 6 complete

Deliverables:

- packaged desktop proof matrix
- final parity audit
- completed capability proof map

Blocking dependencies:

- all earlier phases complete

Required tests:

- packaged validation scenarios
- canonical grouped runner after targeted proof

Proof before close:

- every claimed `done` feature maps to a test or packaged artifact flow
- code clarity gate:
  - shipped names in docs and release outputs remain SplitShot-native
- code completion gate:
  - every claimed shipped feature satisfies the implementation quality contract
- regression gate:
  - targeted and relevant-suite proof both pass before the grouped runner result is used
- release gate:
  - automation-specific release checklist is complete
- parity gate:
  - every adopted outcome claim is backed by proof, and every deferred/rejected outcome is still labeled correctly

## Quality Contract Dependencies

All phases in this roadmap are also governed by:

- [00b-implementation-quality-contract.md](00b-implementation-quality-contract.md)
- [11-release-readiness.md](11-release-readiness.md)
