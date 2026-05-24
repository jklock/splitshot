# Performance Task Backlog

## Usage

- Treat each item as incomplete until its proof exists.
- Link implementation work, test evidence, screenshots, and exported artifacts in `outcome.md` and `artifacts.md`.
- Performance is not done until shared-shell behavior, real data, real persistence, and real docs all agree.

## PRF-001 — Reset the Performance contract

- [x] Rewrite the Performance bundle docs around Stage-shell reuse.
- [x] Replace the standalone Performance-app framing with the graph/info workflow contract.
- [x] Record the internal `library` naming seam and current user-facing Performance naming requirement.
- [x] Mark prior signoff evidence as historical rather than current approval.

Progress note (`2026-05-24`):

- `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, `artifacts.md`, and both Performance prompts now describe Performance as a Stage-shell variant.
- The bundle no longer treats a separate Performance shell family as a requirement.

Depends on:

- none

Proof:

- Performance bundle files updated

## PRF-002 — Reuse the Stage shell grammar

- [ ] Move Performance onto the same shell family as Stage.
- [ ] Place graphs and data in the main area.
- [ ] Use the lower pane for selected-record information.
- [ ] Keep filters, actions, and settings in the right-hand inspector.

Depends on:

- PRF-001

Proof:

- shared-shell Performance static/UI tests updated
- Performance screenshots show Stage-shell reuse clearly

## PRF-003 — Rebuild the record and detail workflow in the new shell

- [ ] Prove loading, refresh, stale, and empty-state behavior.
- [ ] Prove search, sort, and filter behavior.
- [ ] Prove selected-record detail truth in the lower pane.
- [ ] Prove stage/workspace reopen behavior from the new layout.

Depends on:

- PRF-001
- PRF-002

Proof:

- record/detail interaction coverage exists
- screenshots or DOM proof for list/detail state captured

## PRF-004 — Preserve analytics, notes/tags, backup, and export truth

- [ ] Prove note and tag persistence truth through backend routes and the new shell.
- [ ] Prove analytics truth and empty/insufficient-data messaging.
- [ ] Prove backup create/restore behavior.
- [ ] Prove CSV/JSON export behavior and capture updated output artifacts.

Depends on:

- PRF-002
- PRF-003

Proof:

- analytics, persistence, backup, and export tests pass
- output artifacts linked in `artifacts.md`

## PRF-005 — Isolate Performance settings and shared-shell stability

- [ ] Prove Performance settings save and reload behavior.
- [ ] Prove auto-refresh toggle behavior.
- [ ] Prove settings affect Performance only.
- [ ] Keep naming truthful even if the internal `library` storage key remains.

Depends on:

- PRF-001
- PRF-002

Proof:

- settings interaction proof exists
- naming/storage decision is documented in `outcome.md`

## PRF-006 — Sync docs and proof package

- [ ] Update QA matrix for Performance-owned controls and workflows.
- [ ] Update coverage plan and full browser E2E plan.
- [ ] Update user-facing Performance docs.
- [ ] Capture Overview, Records, Detail, Analytics, Backup, and Settings screenshots for the new shell.
- [ ] Record residual risks and waivers.

Depends on:

- PRF-003
- PRF-004
- PRF-005

Proof:

- doc diffs linked in `artifacts.md`
- proof package complete in `outcome.md`

## PRF-007 — Performance done gate

- [ ] Confirm Performance-owned tests are green for the new contract.
- [ ] Confirm shared-shell/backend dependencies used by Performance are green.
- [ ] Confirm reopen, analytics, backup, and export proof artifacts exist for the new shell.
- [ ] Confirm visual approval is recorded.
- [ ] Confirm user-facing naming and doc truth are aligned.

Depends on:

- PRF-006

Proof:

- `outcome.md` final gate marked complete
