# Match Task Backlog

## Usage

- Treat each item as incomplete until its proof exists.
- Link implementation changes, test evidence, screenshots, and output artifacts in `outcome.md` and `artifacts.md`.
- Match is not done until the shared-shell contract, workflow truth, and output proof all agree.

## MCH-001 — Reset the Match contract

- [x] Rewrite the Match bundle docs around Stage-shell reuse.
- [x] Replace the standalone Match-app framing with the tile/info workflow contract.
- [x] Record Stage auto-seed and shared-shell ownership expectations.
- [x] Mark prior Match completion as historical rather than current signoff.

Progress note (`2026-05-24`):

- `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, `artifacts.md`, and both Match prompts now describe Match as a Stage-shell variant.
- The bundle no longer treats a separate Match shell family as a requirement.

Depends on:

- none

Proof:

- Match bundle files updated

## MCH-002 — Reuse the Stage shell grammar

- [ ] Move Match onto the same shell family as Stage.
- [ ] Preserve the persistent rail, right inspector, and lower pane grammar.
- [ ] Remove Match-specific shell-family assumptions from docs/tests/code.
- [ ] Keep footer order and shared-shell status behavior stable.

Depends on:

- MCH-001

Proof:

- shared-shell Match static/UI tests updated
- Match screenshots show Stage-shell reuse clearly

## MCH-003 — Align lifecycle and auto-seed behavior

- [ ] Prove new/open/save workspace flow under the shared shell.
- [ ] Prove stage add/remove/select behavior.
- [ ] Auto-create or attach Match membership when a Stage folder/project is opened.
- [ ] Prove Stage open from Match and return to Match.

Depends on:

- MCH-001
- MCH-002

Proof:

- lifecycle browser and controller tests pass
- Match empty and loaded screenshots refreshed

## MCH-004 — Build the tile and lower-info workflow

- [ ] Render stage/media tiles in the main area.
- [ ] Use the lower pane for selected-tile information instead of a standalone waveform-style shell.
- [ ] Keep Match workflow options in the right-hand inspector.
- [ ] Preserve truthful defaults, overrides, setup-once, and apply-from-first behavior.

Depends on:

- MCH-002
- MCH-003

Proof:

- interaction coverage exists for tile selection and lower-pane truth
- docs describe the final behavior truthfully

## MCH-005 — Close recap, composite, export, and parity gaps

- [ ] Prove recap render success and error paths.
- [ ] Prove composite clip CRUD, align, audio mix, and cut override behavior.
- [ ] Prove batch export queue, recipe, progress, and completion/error behavior.
- [ ] Implement or truthfully defer Match parity gaps: recap merge controls, Auto Trim, Split Sync / Stage Mix orchestration, intro/title/watermark parity, and score-import expansion.

Depends on:

- MCH-003
- MCH-004

Proof:

- recap/composite/export tests pass
- output artifacts linked in `artifacts.md`

## MCH-006 — Isolate Match settings and sync proof

- [ ] Prove Match settings save and reload behavior.
- [ ] Prove Match settings affect Match only.
- [ ] Prove Match settings do not mutate Stage or Performance behavior.
- [ ] Update QA matrix, coverage docs, and user-facing Match documentation.

Depends on:

- MCH-002
- MCH-005

Proof:

- settings interaction proof exists
- doc/audit tests pass

## MCH-007 — Match done gate

- [ ] Confirm Match-owned tests are green for the new contract.
- [ ] Confirm shared-shell/backend dependencies used by Match are green.
- [ ] Confirm recap/export artifacts exist for the new shell.
- [ ] Confirm Stage handoff/return and auto-seed behavior are proven.
- [ ] Confirm visual approval is recorded.

Depends on:

- MCH-006

Proof:

- `outcome.md` final gate marked complete
