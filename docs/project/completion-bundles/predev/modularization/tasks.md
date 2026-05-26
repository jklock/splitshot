# Modularization Task Backlog

## Usage

- Treat each item as incomplete until its proof exists.
- Link source diffs, test evidence, and doc updates in `outcome.md` and `artifacts.md`.
- Modularization is done only when app ownership is enforceable, not when files merely move around.

## MOD-001 — Inventory current shell ownership

- [x] Map current `app.js` responsibilities.
- [x] Map shared runtime responsibilities.
- [x] Map Stage, Match, and Performance ownership seams.
- [x] Identify cross-app DOM queries and hidden state dependencies.

Depends on:

- none

Proof:

- `spec.md` ownership inventory completed
- risk list started in `outcome.md`

Progress note (`2026-05-25`):

- `spec.md` now carries a concrete ownership map for `app.js`, `shell-runtime.js`, `match-view.js`, and `library-view.js` plus the current persistence and DOM-dependency seams.

## MOD-002 — Define stable module interfaces

- [x] Define shared-shell responsibilities.
- [x] Define Stage, Match, and Performance app interfaces.
- [x] Define shared-runtime helper responsibilities.
- [x] Define state hydration and event wiring boundaries.
- [x] Define app-local persistence boundaries.

Depends on:

- MOD-001

Proof:

- `spec.md` dependency and interface rules completed
- app bundles reference the same ownership model

Progress note (`2026-05-25`):

- Shared-shell responsibilities, app-owned interfaces, and local persistence boundaries are now explicit in `spec.md` and reflected in the source/aggregate ledgers.

## MOD-003 — Extract and isolate Stage behavior

- [x] Move or isolate Stage-specific behavior out of generic shell logic where practical.
- [x] Ensure Stage behavior is owned by Stage modules or Stage-focused helpers.
- [x] Remove accidental Match/Performance knowledge from Stage code paths.

Depends on:

- MOD-002

Proof:

- source-level ownership tests or audits pass
- residual Stage coupling is documented if not eliminated

Progress note (`2026-05-25`):

- No Stage reopen was required in this pass. Stage-owned shell/runtime behavior remained isolated to shared-shell and Stage-focused helpers while Match/Performance feature ownership continued moving out of root orchestration.

## MOD-004 — Constrain shared shell behavior

- [x] Keep shared shell focused on landing, switching, global status, and global settings entry.
- [x] Remove accidental app-specific feature ownership from root orchestration.
- [x] Document any remaining shared-shell exceptions.

Depends on:

- MOD-002
- MOD-003

Proof:

- `app.js` ownership boundary is documented and test-backed
- shell-only concerns are explicit in docs

Progress note (`2026-05-25`):

- `app.js` now delegates the live Match and Performance render/helper entry points to `match-view.js` and `library-view.js` first.
- Remaining fallback implementations in `app.js` are documented as temporary compatibility exceptions instead of implicit ownership.

## MOD-005 — Isolate app-local persistence and settings

- [x] Prove Stage, Match, and Performance use separate local persistence or clearly scoped storage keys.
- [x] Prove reloading one app’s settings does not mutate the others.
- [x] Document any migrations or compatibility shims.

Depends on:

- MOD-002
- MOD-004

Proof:

- settings/local-state evidence linked in `artifacts.md`
- app bundles reference isolated settings behavior

Progress note (`2026-05-25`):

- Match and Performance local settings isolation stayed green in the targeted settings packs.
- Performance stale/error recovery now exposes visible shell-level recovery controls without breaking the app-local `splitshot.library.settings` contract.

## MOD-006 — Add modularization proof coverage

- [ ] Add or update source-level ownership tests.
- [ ] Add or update app-owned interaction/e2e coverage affected by modularization.
- [ ] Update docs that explain shell versus app ownership.
- [ ] Record residual risks and waivers.

Depends on:

- MOD-003
- MOD-004
- MOD-005

Proof:

- modularization-related tests pass
- doc diffs linked in `artifacts.md`

## MOD-007 — Modularization done gate

- [ ] Confirm app ownership boundaries are documented and proven.
- [ ] Confirm Stage, Match, and Performance can be reasoned about separately.
- [ ] Confirm shared shell scope is explicit and stable.
- [ ] Confirm approval is recorded.

Depends on:

- MOD-006

Proof:

- `outcome.md` final gate marked complete
