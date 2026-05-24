# Stage Task Backlog

## Usage

- Treat each item as incomplete until the listed proof exists.
- Link implementation changes, test runs, screenshots, and doc updates in `outcome.md` and `artifacts.md`.
- Do not count placeholder UI or route presence alone as completion.

## STG-001 — Reset the Stage contract

- [x] Rewrite the Stage bundle docs around the Stage-first shell.
- [x] Record the required workflow order.
- [x] Record the shared-shell ownership rule for Match and Performance.
- [x] Mark the prior completion framing as superseded by the redesign.

Progress note (`2026-05-24`):

- `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, `artifacts.md`, and both Stage prompts now describe Stage as the canonical shell and workflow contract.
- The bundle no longer treats Match and Performance as separate shell families.
- This closes the bundle-reset documentation lane only; no product code has been signed off under the new contract yet.

Depends on:

- none

Proof:

- Stage bundle files updated

## STG-002 — Remove Project automation clutter

- [ ] Remove the current Stage Automation dump from Project.
- [ ] Keep Project focused on setup, import, and PractiScore.
- [ ] Redistribute displaced controls to PiP, Review, Export, or other logical steps.
- [ ] Ensure no dead placeholder cards remain in Project.

Depends on:

- STG-001

Proof:

- static UI and interaction tests updated
- Project screenshots and docs refreshed

## STG-003 — Harden the shared Stage shell

- [ ] Normalize the shell primitives Match and Performance must reuse.
- [ ] Preserve preview dominance, right inspector, and lower info pane behavior.
- [ ] Remove separate-shell assumptions from the shared layout/runtime code.
- [ ] Keep footer order and shared-shell status behavior stable.

Depends on:

- STG-001

Proof:

- shared shell tests and screenshots updated
- Match and Performance bundles can point at the same shell family without contradiction

## STG-004 — Fix import, home-path, and output defaults

- [ ] Make the selected project folder the default home for file pickers, excluding primary-video import.
- [ ] Rename and implement `Import Primary Video` as a copy into the project Import folder.
- [ ] Default Stage export output to the project Output folder.
- [ ] Preserve the protected PractiScore fallback/session/sync contract.

Depends on:

- STG-002

Proof:

- lifecycle/import/PractiScore tests pass
- user-facing docs reflect the new Project behavior

## STG-005 — Close PiP, Review, marker, and top-bar regressions

- [ ] Show the secondary waveform beneath the primary waveform/info lane when PiP media exists.
- [ ] Default Review PiP on when PiP media exists.
- [ ] Keep Review Splits, Score, and Overlay enabled by default.
- [ ] Fix secondary preview lag/drift.
- [ ] Restore imported/custom summary authoring and the two-column Review styling layout.
- [ ] Separate marker styling from overlay styling.
- [ ] Keep the status/progress bar inside the top bar.

Depends on:

- STG-003
- STG-004

Proof:

- focused browser interaction coverage exists
- screenshots or DOM proof captured where visual behavior matters

## STG-006 — Close Stage-owned parity gaps

- [ ] Implement or truthfully defer Auto Trim.
- [ ] Implement or truthfully defer Split Sync layout parity.
- [ ] Implement or truthfully defer Stage Mix parity.
- [ ] Implement or truthfully defer intro title cards.
- [ ] Implement or truthfully defer custom watermark.
- [ ] Implement or truthfully defer score-import expansion.

Depends on:

- STG-002
- STG-003

Proof:

- owning tests pass or explicit doc corrections exist
- no placeholder UI is counted as completion

## STG-007 — Sync tests, docs, and proof

- [ ] Update Stage-owning browser tests and audits.
- [ ] Update QA matrix, coverage plan, and full browser E2E plan.
- [ ] Update user-facing Stage and Project docs.
- [ ] Capture refreshed Stage screenshots and artifact notes for the redistributed flow.

Depends on:

- STG-004
- STG-005
- STG-006

Proof:

- doc/audit tests pass
- artifact ledger updated in `artifacts.md`

## STG-008 — Stage done gate

- [ ] Confirm Stage-owned tests are green for the new contract.
- [ ] Confirm Match and Performance reuse no longer depends on a stale Stage shell contract.
- [ ] Confirm all required artifacts exist.
- [ ] Confirm visual approval is recorded.
- [ ] Confirm no undocumented Stage-visible regressions remain open.

Depends on:

- STG-007

Proof:

- `outcome.md` final gate marked complete
