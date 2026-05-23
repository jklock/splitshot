# Editor Workflow Specification

This document defines Single Video and Multi Video as one editing system with two scopes.

## Core Model

- `Single Video` is one-stage scope
- `Multi Video` is many-stage match scope
- both reference the same underlying truth objects
- `Performance Library` is outside this workflow and reads the results later

## Single Video Workflow

1. Open one stage record.
2. Import or confirm the primary video.
3. Run or confirm analysis.
4. Correct timing truth as needed.
5. Import or adjust score context.
6. Review overlays, metrics, markers, and output variants.
7. Export one or more derived outputs.

Single Video is the high-detail working view.

## Multi Video Workflow

1. Create or open a match workspace.
2. Add many stage records to that workspace.
3. Set shared match defaults.
4. Review stage completeness and status across the match.
5. Open any stage into focused Single Video when deep per-stage work is required.
6. Return to Multi Video and continue batch consistency work.
7. Export per-stage outputs or match-scope outputs.

Multi Video is the consistency and throughput view.

## Seamless Movement Between Scopes

### Multi to Single

When a user opens a stage from Multi Video:

- the stage opens directly into Single Video
- no conversion or copy is created
- the active stage retains its identity inside the match workspace
- match-level defaults remain visible as inherited context

### Single to Multi

When a user returns from Single Video:

- the edited stage reappears in Multi Video as the same stage record
- updated truth, outputs, and status are visible immediately
- no reconciliation flow should be required

## Truth Ownership

### Always stage-local

The following truth belongs to the stage record itself:

- source media linkage for the stage
- detected and corrected timing truth
- stage scoring truth
- computed stage metrics
- stage-specific analysis notes
- stage-specific output variants

### Match-shared by default

The match workspace should own shared defaults such as:

- preferred export recipe defaults
- subtitle preset defaults
- title-card defaults
- watermark defaults
- layout defaults where match-wide consistency makes sense
- any global batch processing options

### Stage override behavior

If a user changes a shared setting while focused on one stage:

- only that stage receives the override
- sibling stages keep the inherited match value
- the UI must expose whether the stage value is inherited or overridden

## Inheritance and Override Rules

The implementation should preserve these rules:

- every match-shared field has a default workspace value
- every stage can optionally carry an override for eligible fields
- absence of a stage override means the stage inherits the match value
- resetting a stage field removes the override and reverts to inherited behavior

## Output Recipe Scope

### Stage-scoped outputs

These are outputs tied to a single stage record:

- trimmed stage recap
- dense technical review export
- clean social-style export
- comparison export for a dual-angle stage

### Match-scoped outputs

These are outputs derived from many stages:

- stage montage
- match recap
- batch-exported per-stage set using one shared recipe family

## Acceptance Criteria

- A stage opens from Multi into Single without duplication.
- Returning to Multi reflects the same stage's updated truth immediately.
- Shared match settings apply by default to all stages.
- Stage overrides affect only the edited stage.
- Output recipes can be resolved clearly at stage scope vs match scope.

## Current Repo Seams To Extend

- `src/splitshot/domain/models.py`
  - current `Project` remains the stage-level truth contract.
- `src/splitshot/persistence/projects.py`
  - current project bundle handling remains the stage-bundle persistence base.
- `src/splitshot/ui/controller.py`
  - current controller already owns save/open/autosave and settings-layer resolution.
- `src/splitshot/browser/state.py`
  - current `/api/state` must expand from single-stage payload to editor-scope payload.
- `src/splitshot/browser/server.py`
  - current project routes remain supported; workspace routes are additive.

## Exact Editor-Scope Contract

### Authoritative truth model

- A `Project` instance remains the editable truth for one stage.
- `Multi Video` never edits a sibling stage by duplicating its `Project`.
- Opening a stage from `Multi Video` loads that stage's `Project` into the same stage editor used by `Single Video`.
- Returning to `Multi Video` restores workspace context and displays the same `stage_id` with updated status.

### Required browser state additions

`/api/state` must add:

- `editor_scope`
  - `single` or `multi`
- `active_stage_id`
- `active_match_id`
- `opened_from_match`
- `return_to_match_available`
- `match_workspace_summary`
- `stage_workspace_status`
- `inherited_setting_status`
- `output_profile_summary`

### Required route additions

- `/api/workspace/new`
  - create a new match workspace
- `/api/workspace/open`
  - open an existing match workspace
- `/api/workspace/save`
  - persist workspace metadata and stage membership
- `/api/workspace/stage/open`
  - open one `stage_id` from a match into the stage editor
- `/api/workspace/stage/return`
  - return from stage editor to the last active workspace context
- `/api/workspace/defaults`
  - update match-level shared defaults
- `/api/workspace/stage/override`
  - set one stage-local override
- `/api/workspace/stage/override/reset`
  - remove one stage-local override and return to inheritance

### Required route behavior

- every workspace route must autosave the workspace bundle after a successful mutation
- opening a stage from a workspace must not create a new `Project.id`
- stage-open failures must return a structured error containing:
  - `match_id`
  - `stage_id`
  - `reason`
- return-to-workspace must restore the previously selected stage row and filter state

## Persistence And Compatibility Contract

### Single-stage compatibility

- Existing project folders containing `project.json` continue to open directly into `Single Video`.
- No migration step is required for legacy single-stage bundles.
- A stage opened from a match workspace uses the same `project.json` schema plus additional workspace linkage metadata defined in [04-data-model-spec.md](04-data-model-spec.md).

### Match workspace layout

- A match workspace is a folder containing `workspace.json`.
- Stage records are stored under `Stages/<stage_id>/project.json`.
- Match-scope output artifacts are stored under `Output/Match/`.
- Workspace-managed per-stage exports are stored under `Output/Stages/<stage_id>/`.

## UI Behavior And Failure States

- The UI must always display whether the user is in `Single Video` or `Multi Video`.
- When a setting is inherited, the UI must show the resolved value and its source.
- When a setting is overridden, the UI must show:
  - the overridden value
  - a reset-to-inherited action
- If a stage record is missing from disk, the workspace row must remain visible with an error state rather than silently disappearing.
- If a workspace opens with one or more missing media paths, the workspace remains usable while those stages are marked incomplete.

## Required Tests And Proof

- persistence test: legacy `project.json` bundle still opens unchanged
- persistence test: workspace folder saves and reloads stable `stage_id` membership
- browser test: open stage from workspace and return without id changes
- browser test: stage override changes one stage only
- browser test: reset override restores inherited value for that stage only
- browser proof: workspace row selection survives stage open and return
