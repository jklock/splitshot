# Match Specification

## Normative statement

Match is a Stage-shell variant for multi-stage organization, recap, composite, and export work. It must not define a separate shell family from Stage.

## Match shell requirements

### Layout grammar

The Match app must provide:

- the same shell family as Stage
- a tile-based main content area for stage/media selection
- a lower pane that shows information about the selected tile above it
- a right-hand inspector that contains Match workflow controls
- footer order `Home` then `Settings`
- a visible empty state when no workspace is open

### Ownership requirements

- Match-specific behavior must stay inside Match-owned modules and routes.
- Stage owns the canonical shell grammar reused by Match.
- Shared shell may switch views and show global status only.

## Workspace lifecycle and auto-seed requirements

- New workspace, open workspace, and save workspace flows must be available from Match-owned entry points.
- Stage add/remove/select behavior must be deterministic.
- Stage removal must require confirmation.
- When a Stage folder/project is created or opened, Match must auto-create or attach the owning workspace entry so the stage self-registers into Match.
- Empty-state, loading-state, and recoverable error-state behavior must exist for workspace lifecycle operations.

## Stage handoff requirements

- Opening a stage from Match must preserve workspace identity and stage membership.
- Match must expose a reliable return-to-workspace path after Stage editing.
- Match completion must not depend on hidden shell state to restore the active workspace.

## Tile and lower-pane requirements

- The main area must show Match tiles rather than a separate standalone shell layout.
- Selecting a tile must populate the lower information pane truthfully.
- Match workflow options must live in the right-hand inspector rather than disjoint panels.

## Shared defaults and override requirements

- Shared defaults must apply across the workspace without mutating unrelated settings.
- Stage overrides must apply to one stage only.
- Override reset must restore inheritance behavior.
- Setup-once banner behavior must be truthful.
- `apply-from-first` preview and apply behavior must be explicitly proven and documented.

## Recap, composite, and batch export requirements

- Recap must allow stage inclusion selection and surface success/error states.
- Composite clip list must reflect persisted clip state.
- Clip add, update, remove, align, audio mix, and cut override behavior must be deterministic.
- Batch export must show the current queue truthfully.
- Select all / none controls must affect the queue deterministically.
- Recipe selection must map to backend export behavior.
- Export progress, completion, and failure states must be visible.

## Match parity requirements

The following Match-visible features must be implemented where they belong in the Match workflow or explicitly documented as deferred:

- recap merge gaps such as per-clip subtitle, drag reorder, and independent audio controls
- recap Auto Trim
- Split Sync / Stage Mix orchestration at Match scope
- intro/title/watermark parity at recap/export scope
- batch export parity
- score-import expansion where Match depends on it

## Match settings requirements

- Match settings must be stored under `splitshot.match.settings` unless a coordinated migration is implemented.
- Match settings must affect Match only.
- Match settings must not mutate Stage shell defaults or Performance behavior.

## Documentation and contract requirements

Any Match-visible shell or workflow change requires synchronized updates to:

- Match-owning browser tests
- browser control inventory and coverage audits where affected
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- user-facing Match docs where behavior changed

## Test requirements

At minimum, Match reset work must be backed by:

- static UI contract coverage for shared-shell Match markup and ids
- workspace lifecycle/controller coverage
- interaction/e2e coverage for Match navigation, tile selection, and Stage handoff
- recap/composite/export coverage where behavior is claimed complete
- doc-audit and control-inventory coverage where Match controls changed

## Definition of specification success

The Match spec is satisfied only when Match UI behavior, shared-shell layout, workspace/backend truth, tests, docs, and output artifacts all describe the same Match product model.
