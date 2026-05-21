# Match Video Edit Feature Specification

Match Video Edit is the match-level batch editor and manager.

## Definition

Match Video Edit means:

- many stages from one match
- shared settings across those stages
- stage-local overrides when needed
- stage-level truth preserved independently
- **setup on the first stage, apply to all others**

It does **not** mean only alternate camera sync.

## Core Responsibilities

### 1. Match workspace creation

Need a match workspace that can:

- create many stage records quickly
- attach source videos to each stage
- preserve match and stage relationships
- auto-name stages from PracticeScore data when available

### 2. Stage grid with status

Need a visual overview showing:

- all stages in the match
- completeness status (missing, needs review, ready, custom)
- missing media indicators
- override indicators
- last reviewed timestamp
- drag-and-drop reordering

### 3. Shared settings

Need match-level shared defaults for:

- output recipe families
- subtitle defaults
- title-card defaults
- watermark defaults
- batch export defaults
- trim dead time defaults
- video shape defaults

### 4. Setup Once, Apply Everywhere

Need a workflow where:

- user configures Stage 1 completely
- user returns to match grid
- SplitShot offers to apply Stage 1's settings to all other stages
- user confirms with a preview of changes
- all stages receive the settings
- stages show "shared" badge

### 5. Stage overrides

Need stage-local override support with explicit inherited vs overridden state.

### 6. Stage-to-stage consistency

Need workflows for:

- applying one recipe across many stages
- seeing which stages diverge
- normalizing outputs across a match quickly
- batch export with progress

### 7. Match-level outputs

Need both:

- per-stage outputs (batch)
- match-scope outputs (recap, montage)

## Match Video Edit Layout

The Match Video Edit surface should present:

### Header

- match name and date
- match-level scoring summary (total time, total penalties, hit factor)
- action buttons: Save, Export All, Build Recap

### Stage Grid

- table or card grid of all stages
- columns:
  - stage number
  - stage name
  - video thumbnail
  - status badge
  - settings badge (shared / custom / missing)
  - scoring summary
  - actions: Open, Override, Reset, Remove

### Setup Panel

- shows Stage 1's configuration
- "Apply to All Stages" button
- preview of what will change
- confirmation dialog

### Shared Defaults Panel

- editable defaults for the whole match
- shows which stages are using defaults vs. overrides
- reset-all button

### Batch Export Panel

- select which stages to export
- choose output recipe
- see export queue with progress
- cancel individual or all exports

### Match Recap Builder

- stage inclusion/exclusion
- stage order
- result-card configuration
- transition style
- preview before render

## Competitor Feature Placement

### Line Up Angles

Line Up Angles belongs in Match Video Edit when the use case is:

- same-stage dual-angle comparison
- POV vs follow-cam alignment
- auto-sync by beep

The implementation should still allow drill-down into Stage Video Edit for one stage.

### Smart Angle Switching

Smart Angle Switching belongs in Match Video Edit when the use case is:

- 3+ angles for one stage or match package
- role labels such as `Primary`, `Follow`, `Static`
- auto-cut plan generation
- manual cut override

### Match Recap and Stage Composite

Match Video Edit must explicitly separate two possible meanings:

1. `Match Recap`
   - many stages stitched into one recap
2. `Stage Composite`
   - many clips combined for one stage-specific result

First delivery supports both flows.
They must be implemented, documented, tested, and proven separately.

### Audio Balance

Needed for recap or angle-directed outputs.

### Result Cards

Needed when montage outputs need stage-specific summaries or transitions.

## Output Model For Match Video Edit

Need both:

- per-stage outputs
- match-scope outputs

Per-stage outputs:

- same recipe across all stages
- stage-specific variants when overridden

Match-scope outputs:

- Match Recap
- highlight package
- later Smart Angle Switching outputs where applicable

## Setup Once, Apply Everywhere Contract

### Trigger

The action becomes available when:

- Stage 1 has been configured with at least one output profile
- there are 2 or more stages in the match
- Stage 1's settings have changed since the last apply

### Eligible Settings

These settings can be applied from Stage 1 to siblings:

- `trim_dead_time` (lead-in and tail padding)
- `shot_data_overlay` (preset and visibility)
- `video_shape` (aspect ratio)
- `opening_title` (content and style)
- `your_logo` (source, position, opacity)
- `overlay_visibility` (which badges show)
- `overlay_position` (badge positions)
- `marker_visibility` (which markers show)
- `export_quality` (codec, bitrate)

These settings are **never** applied:

- timing truth
- scoring truth
- shot positions
- stage-specific markers
- per-shot scores

### Preview

Before applying, show:

- list of stages that will be updated
- for each stage, which settings will change
- count of unchanged stages
- warning for stages with existing overrides

### Application

- settings are copied as match-shared defaults
- stages without overrides adopt the new defaults
- stages with overrides keep their overrides
- stages show "shared" badge after application
- user can later override any stage individually

### Reset

- user can reset any stage to match-shared defaults
- user can reset all stages to match-shared defaults
- reset removes stage-local overrides

## Technical Acceptance Criteria

- A match workspace can own many stage records.
- Shared settings apply across all stages until locally overridden.
- Line Up Angles can operate at same-stage dual-angle scope without breaking the match workspace model.
- Smart Angle Switching can own role labels and cut-plan overrides when implemented.
- Match-scope outputs can be defined without duplicating underlying stage truth.
- Setup Once, Apply Everywhere copies only eligible settings.
- Stages show correct badges after apply and override.
- Batch export processes stages sequentially and reports progress.

## SplitShot-Native Implementation Labels

Use these labels in implementation-facing work:

- `Match Workspace`
- `Line Up Angles`
- `Match Recap`
- `Stage Composite`
- `Smart Angle Switching`
- `Camera Jobs`
- `Audio Balance`
- `Result Cards`
- `Setup Once Apply Everywhere`
- `Stage Grid`
- `Batch Export`

## Current Repo Seams To Extend

- `src/splitshot/domain/models.py`
- `src/splitshot/persistence/projects.py`
- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/browser/server.py`
- `src/splitshot/browser/static/panes/project-pane.js`
- `src/splitshot/browser/static/panes/merge-pane.js`
- `src/splitshot/export/pipeline.py`

## Exact Workflow Separation

### Match Recap

`Match Recap` is the many-stage package workflow.

It must:

- source clips from multiple `stage_id` values in one `match_id`
- preserve stage ordering from workspace state
- allow shared recap profile settings plus stage-local inclusion/exclusion
- support Result Cards between or within stage segments
- show a preview of the final sequence before render

### Stage Composite

`Stage Composite` is the one-stage multi-clip workflow.

It must:

- source multiple clips for one `stage_id`
- allow same-stage composition across many angles or source segments
- preserve one authoritative stage timing/scoring truth
- attach clip-local sync/alignment and audio-mix decisions without forking stage truth
- show a preview of the composite before render

The implementation agent must treat `Match Recap` and `Stage Composite` as separate product flows, separate route handlers, and separate proof targets.

## Exact Feature Contracts

### Match Workspace

- owns `match_id`
- owns stage membership and ordering
- owns shared defaults
- owns first-stage snapshot
- owns stage override maps
- owns match-scope output profiles

### Line Up Angles

- applies to same-stage multi-angle alignment only
- stores offset and analyzed-source metadata per clip source
- does not imply match-wide editing

### Smart Angle Switching

- produces a suggested cut plan for multi-angle review
- suggested cuts are editable
- accepted cut decisions persist in the relevant output profile, not in stage truth

### Camera Jobs

Required first-delivery role set:

- `primary`
- `follow`
- `static`
- `detail`

### Audio Balance

- persist per clip source inside `Stage Composite` or `Match Recap`
- control gain, mute, and selected-primary-audio source
- do not alter saved source media

### Result Cards

- summarize stage/result context inside recap outputs
- source all metric values from reviewed truth
- may be disabled per output profile
- configurable style and position

### Setup Once Apply Everywhere

- triggered by explicit user action
- copies eligible settings from Stage 1 to match-shared defaults
- updates all stages without overrides
- preserves existing overrides
- shows preview before applying
- logs which stages were updated

## Required Routes

### Workspace routes

- `/api/workspace/stage/add`
- `/api/workspace/stage/remove`
- `/api/workspace/defaults`
- `/api/workspace/stage/override`
- `/api/workspace/stage/override/reset`
- `/api/workspace/apply-from-first`
- `/api/workspace/apply-from-first/preview`

### Match Recap routes

- `/api/output-profiles/create` with `scope_type=match`
- `/api/output-profiles/render` with `profile_kind=match_recap`
- `/api/match-recap/preview`

### Stage Composite routes

- `/api/output-profiles/create` with `scope_type=stage`
- `/api/output-profiles/render` with `profile_kind=stage_composite`
- `/api/workspace/stage/clip/add`
- `/api/workspace/stage/clip/update`
- `/api/workspace/stage/clip/remove`
- `/api/stage-composite/preview`

### Batch export routes

- `/api/batch-export/start`
- `/api/batch-export/status`
- `/api/batch-export/cancel`

## UI Behavior And Failure States

- Workspace rows must show whether a stage is:
  - complete
  - incomplete
  - missing media
  - overridden
- A missing clip in `Stage Composite` invalidates only that output profile, not the whole workspace.
- Removing a stage from a workspace never deletes the underlying stage folder automatically.
- A recap render with zero included stages must fail validation before export begins.
- Batch export must skip stages with missing media and report them in the completion summary.
- Apply-from-first must not apply if Stage 1 has no eligible configuration.
- Apply-from-first must warn if some stages already have overrides.

## Required Tests And Proof

- workspace membership save/load
- inherited defaults across many stages
- one-stage override isolation
- same-stage Line Up Angles persistence
- Match Recap render over multiple stages
- Stage Composite render over multiple clips for one stage
- Result Card rendering from reviewed truth
- Setup Once Apply Everywhere copies eligible settings only
- Batch export processes stages and reports progress
- Stage grid drag-and-drop reordering persists
