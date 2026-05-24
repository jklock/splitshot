# Modularization Task Backlog

## Usage

- Treat each item as incomplete until its proof exists.
- Link source diffs, test evidence, and doc updates in `outcome.md` and `artifacts.md`.
- Modularization is done only when app ownership is enforceable, not when files merely move around.

## MOD-001 — Inventory current shell ownership

- [ ] Map current `app.js` responsibilities.
- [ ] Map shared runtime responsibilities.
- [ ] Map Stage, Match, and Performance ownership seams.
- [ ] Identify cross-app DOM queries and hidden state dependencies.

Depends on:

- none

Proof:

- `spec.md` ownership inventory completed
- risk list started in `outcome.md`

## MOD-002 — Define stable module interfaces

- [ ] Define shared-shell responsibilities.
- [ ] Define Stage, Match, and Performance app interfaces.
- [ ] Define shared-runtime helper responsibilities.
- [ ] Define state hydration and event wiring boundaries.
- [ ] Define app-local persistence boundaries.

Depends on:

- MOD-001

Proof:

- `spec.md` dependency and interface rules completed
- app bundles reference the same ownership model

## MOD-003 — Extract and isolate Stage behavior

- [ ] Move or isolate Stage-specific behavior out of generic shell logic where practical.
- [ ] Ensure Stage behavior is owned by Stage modules or Stage-focused helpers.
- [ ] Remove accidental Match/Performance knowledge from Stage code paths.

Depends on:

- MOD-002

Proof:

- source-level ownership tests or audits pass
- residual Stage coupling is documented if not eliminated

## MOD-004 — Constrain shared shell behavior

- [ ] Keep shared shell focused on landing, switching, global status, and global settings entry.
- [ ] Remove accidental app-specific feature ownership from root orchestration.
- [ ] Document any remaining shared-shell exceptions.

Depends on:

- MOD-002
- MOD-003

Proof:

- `app.js` ownership boundary is documented and test-backed
- shell-only concerns are explicit in docs

## MOD-005 — Isolate app-local persistence and settings

- [ ] Prove Stage, Match, and Performance use separate local persistence or clearly scoped storage keys.
- [ ] Prove reloading one app’s settings does not mutate the others.
- [ ] Document any migrations or compatibility shims.

Depends on:

- MOD-002
- MOD-004

Proof:

- settings/local-state evidence linked in `artifacts.md`
- app bundles reference isolated settings behavior

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
