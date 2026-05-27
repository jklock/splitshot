# Multi Video Feature Specification

Multi Video is the match-level editor.

## Definition

Multi Video means:

- many stages from one match
- shared settings across those stages
- stage-local overrides when needed
- stage-level truth preserved independently

It does **not** mean only alternate camera sync.

## Core Responsibilities

### 1. Batch match ingest

Need a match workspace that can:

- create many stage records quickly
- attach source videos to each stage
- preserve match and stage relationships

### 2. Shared settings

Need match-level shared defaults for:

- output recipe families
- subtitle defaults
- title-card defaults
- watermark defaults
- batch export defaults

### 3. Stage overrides

Need stage-local override support with explicit inherited vs overridden state.

### 4. Stage-to-stage consistency

Need workflows for:

- applying one recipe across many stages
- seeing which stages diverge
- normalizing outputs across a match quickly

## Competitor Feature Placement

### Angle Align

Angle Align belongs in Multi Video when the use case is:

- same-stage dual-angle comparison
- POV vs follow-cam alignment
- auto-sync by beep

The implementation should still allow drill-down into Single Video for one stage.

### Angle Director

Angle Director belongs in Multi Video when the use case is:

- 3+ angles for one stage or match package
- role labels such as `POV`, `Follow`, `Static`
- auto-cut plan generation
- manual cut override

### Match Recap and Stage Composite

Multi Video must explicitly separate two possible meanings:

1. `Match Recap`
   - many stages stitched into one recap
2. `Stage Composite`
   - many clips combined for one stage-specific result

First delivery supports both flows.
They must be implemented, documented, tested, and proven separately.

### Audio Mix Lanes

Needed for recap or angle-directed outputs.

### Result Cards

Needed when montage outputs need stage-specific summaries or transitions.

## Output Model For Multi Video

Need both:

- per-stage outputs
- match-scope outputs

Per-stage outputs:

- same recipe across all stages
- stage-specific variants when overridden

Match-scope outputs:

- Match Recap
- highlight package
- later Angle Director outputs where applicable

## Technical Acceptance Criteria

- A match workspace can own many stage records.
- Shared settings apply across all stages until locally overridden.
- Angle Align can operate at same-stage dual-angle scope without breaking the match workspace model.
- Angle Director can own role labels and cut-plan overrides when implemented.
- Match-scope outputs can be defined without duplicating underlying stage truth.

## SplitShot-Native Implementation Labels

Use these labels in implementation-facing work:

- `Match Workspace`
- `Angle Align`
- `Match Recap`
- `Stage Composite`
- `Angle Director`
- `Angle Roles`
- `Audio Mix Lanes`
- `Result Cards`

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

### Stage Composite

`Stage Composite` is the one-stage multi-clip workflow.

It must:

- source multiple clips for one `stage_id`
- allow same-stage composition across many angles or source segments
- preserve one authoritative stage timing/scoring truth
- attach clip-local sync/alignment and audio-mix decisions without forking stage truth

The implementation agent must treat `Match Recap` and `Stage Composite` as separate product flows, separate route handlers, and separate proof targets.

## Exact Feature Contracts

### Match Workspace

- owns `match_id`
- owns stage membership and ordering
- owns shared defaults
- owns stage override maps
- owns match-scope output profiles

### Angle Align

- applies to same-stage multi-angle alignment only
- stores offset and analyzed-source metadata per clip source
- does not imply match-wide editing

### Angle Director

- produces a suggested cut plan for multi-angle review
- suggested cuts are editable
- accepted cut decisions persist in the relevant output profile, not in stage truth

### Angle Roles

Required first-delivery role set:

- `primary`
- `follow`
- `static`
- `detail`

### Audio Mix Lanes

- persist per clip source inside `Stage Composite` or `Match Recap`
- control gain, mute, and selected-primary-audio source
- do not alter saved source media

### Result Cards

- summarize stage/result context inside recap outputs
- source all metric values from reviewed truth
- may be disabled per output profile

## Required Routes

### Workspace routes

- `/api/workspace/stage/add`
- `/api/workspace/stage/remove`
- `/api/workspace/defaults`
- `/api/workspace/stage/override`
- `/api/workspace/stage/override/reset`

### Match Recap routes

- `/api/output-profiles/create` with `scope_type=match`
- `/api/output-profiles/render` with `profile_kind=match_recap`

### Stage Composite routes

- `/api/output-profiles/create` with `scope_type=stage`
- `/api/output-profiles/render` with `profile_kind=stage_composite`
- `/api/workspace/stage/clip/add`
- `/api/workspace/stage/clip/update`
- `/api/workspace/stage/clip/remove`

## UI Behavior And Failure States

- Workspace rows must show whether a stage is:
  - complete
  - incomplete
  - missing media
  - overridden
- A missing clip in `Stage Composite` invalidates only that output profile, not the whole workspace.
- Removing a stage from a workspace never deletes the underlying stage folder automatically.
- A recap render with zero included stages must fail validation before export begins.

## Required Tests And Proof

- workspace membership save/load
- inherited defaults across many stages
- one-stage override isolation
- same-stage Angle Align persistence
- Match Recap render over multiple stages
- Stage Composite render over multiple clips for one stage
- Result Card rendering from reviewed truth
