# Editor Workflow Specification v2

This document defines Stage Video Edit and Match Video Edit as one editing system with two scopes, plus the Landing Page as the entry surface.

## Core Model

- `Landing Page` is the entry surface
- `Stage Video Edit` is one-stage scope
- `Match Video Edit` is many-stage match scope
- both reference the same underlying truth objects
- `Performance Library` is outside this workflow and reads the results later

## Landing Page Workflow

1. Open SplitShot.
2. See the Landing Page with three clear choices.
3. Choose `Stage Video Edit` to start editing one stage.
4. Choose `Match Video Edit` to start or continue a match.
5. Choose `Performance Library` to browse history.
6. See recent activity for fast return to previous work.

The Landing Page must never block the user. Every choice must be available immediately.

## Stage Video Edit Workflow

1. Open one stage record (from Landing Page, Match Video Edit, or Performance Library).
2. Import or confirm the primary video.
3. Run or confirm analysis.
4. Correct timing truth as needed.
5. Import or adjust score context.
6. Review overlays, metrics, markers, and output variants.
7. Configure output settings (Trim Dead Time, Shot Data Overlay, Video Shape, Opening Title, Your Logo, etc.).
8. Export one or more derived outputs.
9. Save to Performance Library automatically.

Stage Video Edit is the high-detail working view.

## Match Video Edit Workflow

1. Create or open a match workspace (from Landing Page or scratch).
2. Add many stage records to that workspace.
3. **Configure the first stage completely** — set output settings, overlays, trims, etc.
4. **Apply those settings to all other stages** with one action.
5. Review stage completeness and status across the match.
6. Open any stage into focused Stage Video Edit when deep per-stage work is required.
7. Return to Match Video Edit and continue batch consistency work.
8. Export per-stage outputs or match-scope outputs.
9. Save match to Performance Library automatically.

Match Video Edit is the consistency and throughput view.

### The Setup Once, Apply Everywhere Flow

This is the signature Match Video Edit workflow:

1. User adds all stage videos to the match.
2. User selects Stage 1 and opens it.
3. User configures all desired settings:
   - Trim Dead Time (lead-in and tail padding)
   - Shot Data Overlay preset
   - Video Shape (aspect ratio)
   - Opening Title content
   - Your Logo position and opacity
   - overlay badge positions
   - marker visibility
   - any other output settings
4. User returns to Match Video Edit.
5. SplitShot detects that Stage 1 has configuration and offers: **"Apply Stage 1's settings to all other stages?"**
6. User confirms.
7. SplitShot copies all applicable settings to every other stage.
8. Stages that received settings show a "shared" badge.
9. User can open any stage and override specific settings. Overridden stages show a "custom" badge.
10. User can reset any stage back to shared settings.

### Visual Status Indicators

Each stage in the match grid must show:

- `missing` — no video imported
- `needs review` — video imported, analysis incomplete or unreviewed
- `ready` — analysis reviewed, settings applied
- `custom` — has local overrides
- `error` — media missing or analysis failed

## Seamless Movement Between Scopes

### Landing Page to Editor

- choosing `Stage Video Edit` opens the stage editor (blank or recent)
- choosing `Match Video Edit` opens the match workspace list or creates new
- choosing `Performance Library` opens the library browser

### Match to Stage

When a user opens a stage from Match Video Edit:

- the stage opens directly into Stage Video Edit
- no conversion or copy is created
- the active stage retains its identity inside the match workspace
- match-level defaults remain visible as inherited context
- a "Return to Match" button is always visible

### Stage to Match

When a user returns from Stage Video Edit:

- the edited stage reappears in Match Video Edit as the same stage record
- updated truth, outputs, and status are visible immediately
- no reconciliation flow should be required
- if settings were changed, offer to apply to all other stages again

### Editor to Library

When a user saves a stage or match:

- Performance Library updates automatically
- no manual "add to library" step
- library records link back to the editor source

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
- settings applied from Stage 1 are treated as match-shared defaults

## Output Recipe Scope

### Stage-scoped outputs

These are outputs tied to a single stage record:

- trimmed stage recap
- dense technical review export
- clean social-style export
- branded title-card export
- comparison export for a dual-angle stage

### Match-scoped outputs

These are outputs derived from many stages:

- stage montage
- match recap
- batch-exported per-stage set using one shared recipe family

## Acceptance Criteria

- A stage opens from Match into Stage without duplication.
- Returning to Match reflects the same stage's updated truth immediately.
- Shared match settings apply by default to all stages.
- Stage overrides affect only the edited stage.
- Output recipes can be resolved clearly at stage scope vs match scope.
- The Landing Page is always accessible and never blocks editor work.
- Setup Once, Apply Everywhere copies all applicable settings from Stage 1 to all siblings.
- Stages show clear visual badges for inherited vs overridden vs missing status.

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
- `Match Video Edit` never edits a sibling stage by duplicating its `Project`.
- Opening a stage from `Match Video Edit` loads that stage's `Project` into the same stage editor used by `Stage Video Edit`.
- Returning to `Match Video Edit` restores workspace context and displays the same `stage_id` with updated status.

### Required browser state additions

`/api/state` must add:

- `editor_scope`
  - `landing`, `stage`, `match`, or `library`
- `active_stage_id`
- `active_match_id`
- `opened_from_match`
- `return_to_match_available`
- `match_workspace_summary`
- `stage_workspace_status`
- `inherited_setting_status`
- `output_profile_summary`
- `landing_recent_activity`

### Required route additions

- `/api/landing/recent`
  - list recent stages, matches, and library records
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
- `/api/workspace/apply-from-first`
  - apply Stage 1's settings to all other stages in the match

### Required route behavior

- every workspace route must autosave the workspace bundle after a successful mutation
- opening a stage from a workspace must not create a new `Project.id`
- stage-open failures must return a structured error containing:
  - `match_id`
  - `stage_id`
  - `reason`
- return-to-workspace must restore the previously selected stage row and filter state
- apply-from-first must copy only eligible settings (not timing truth, not scoring truth)

## Persistence And Compatibility Contract

### Single-stage compatibility

- Existing project folders containing `project.json` continue to open directly into `Stage Video Edit`.
- No migration step is required for legacy single-stage bundles.
- A stage opened from a match workspace uses the same `project.json` schema plus additional workspace linkage metadata defined in [04-data-model-spec.md](04-data-model-spec.md).

### Match workspace layout

- A match workspace is a folder containing `workspace.json`.
- Stage records are stored under `Stages/<stage_id>/project.json`.
- Match-scope output artifacts are stored under `Output/Match/`.
- Workspace-managed per-stage exports are stored under `Output/Stages/<stage_id>/`.

## UI Behavior And Failure States

- The UI must always display whether the user is in `Stage Video Edit`, `Match Video Edit`, or `Performance Library`.
- When a setting is inherited, the UI must show the resolved value and its source.
- When a setting is overridden, the UI must show:
  - the overridden value
  - a reset-to-inherited action
- If a stage record is missing from disk, the workspace row must remain visible with an error state rather than silently disappearing.
- If a workspace opens with one or more missing media paths, the workspace remains usable while those stages are marked incomplete.
- The Setup Once, Apply Everywhere action must show a preview of what will change before applying.
- If Stage 1 has no configuration, the apply action must be disabled with a helpful message.

## Required Tests And Proof

- persistence test: legacy `project.json` bundle still opens unchanged
- persistence test: workspace folder saves and reloads stable `stage_id` membership
- browser test: open stage from workspace and return without id changes
- browser test: stage override changes one stage only
- browser test: reset override restores inherited value for that stage only
- browser test: apply-from-first copies settings to all siblings
- browser proof: workspace row selection survives stage open and return
- browser proof: Landing Page shows recent activity correctly
