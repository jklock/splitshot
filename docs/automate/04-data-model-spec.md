# Data Model Specification

This document defines the technical model additions required by the SplitShot automation plan.

## Project Hierarchy

### Single-stage project

Represents one stage or run.

Owns:

- stage truth
- stage media links
- stage scoring and metrics
- stage output variants

### Multi-stage match workspace

Represents one match-level editing container.

Owns:

- match identity
- membership of many stage records
- shared match defaults
- optional match-scope outputs

### Library record

Represents the durable historical record for a stage, match, or output family.

Owns:

- long-term indexed metadata
- linkage to retained proxies
- linkage back to active editor truth

## Required Ids

- `run_id` — stable id for one analyzed run record
- `stage_id` — stable stage identity, even inside a match
- `match_id` — stable match workspace identity
- `output_id` — stable id for one named output variant
- `library_record_id` — stable id for one persisted historical record
- `retained_proxy_id` — stable id for one review proxy artifact

## Relationship Model

- one `match_id` can contain many `stage_id` values
- one `stage_id` resolves to one authoritative reviewed stage truth
- one `stage_id` can have many `output_id` values
- one stage or match can map to one or more `library_record_id` values as needed by the final schema
- one `output_id` can reference zero or one active retained proxy, while a stage record can also keep a stage-level retained proxy

## Settings Inheritance Model

### Global defaults

Stored as app-level defaults.

### Match-shared defaults

Stored on the match workspace.

### Stage-local overrides

Stored only when a stage diverges from the shared value.

### Rule

For eligible fields:

- if no stage override exists, resolve from match-shared default
- if no match-shared default exists, resolve from global default
- if a stage override exists, it wins for that stage only

## Output Model

Each reviewed truth record can produce many named output variants.

Minimum output fields:

- `output_id`
- `scope_type` — `stage` or `match`
- `scope_id`
- `output_type`
- `name`
- `aspect_ratio_preset`
- `frame_preset`
- `overlay_visibility_preset`
- `subtitle_preset`
- `watermark_config`
- `title_card_config`
- `retained_proxy_id`
- `last_rendered_at`

## Retained Artifact Model

### Proxy metadata

Minimum proxy fields:

- `retained_proxy_id`
- `scope_type`
- `scope_id`
- `source_output_id` when proxy derives from an output variant
- `relative_path`
- `codec_profile`
- `width`
- `height`
- `duration_ms`
- `file_size_bytes`
- `generated_from_truth_hash`
- `generated_at`

### Regeneration triggers

Proxy refresh should trigger when reviewed truth changes in ways that affect useful playback:

- timing truth
- score summary shown in proxy overlay
- subtitle preset
- overlay visibility recipe
- watermark or title card where those are part of proxy policy

### Lifecycle

The retained proxy contract is:

- one active latest proxy per scope
- invalidate the active proxy when the truth hash changes
- rebuild when the active proxy is stale or missing

## Library Metric Index Model

The historical metric index should persist normalized values for comparison, at minimum:

- first-shot reaction
- cumulative time
- split list summary
- reload count and reload durations when derived
- transition counts and durations when derived
- score totals
- penalties
- final score deltas and derived comparisons when applicable

## Required Interfaces

### Editor to library

Need a stable transformation from:

- Single Video stage truth
- Multi Video match and stage truth

into:

- library stage record
- library match record
- library metric indexes

### Output to proxy

Need a stable transformation from:

- output variant configuration
- reviewed truth

into:

- retained review proxy artifact
- proxy metadata record

### Multi to stage references

Need stable references so a stage inside Multi Video can always resolve to the same stage truth opened in Single Video.

### Reopen safety

Minimum metadata required to reopen safely:

- stable ids
- workspace relationship metadata
- media linkage metadata
- last known truth metadata

## Acceptance Criteria

- The schema distinguishes single-stage records, match workspaces, and library records.
- Inheritance rules can be implemented deterministically.
- Output variants can be stored without duplicating stage truth.
- Retained proxies can be invalidated and rebuilt deterministically.

## Exact Model Decisions

### Stage truth

- `Project` remains the stage-level truth object.
- The existing `Project.id` remains the primary stable `stage_id` for legacy and new single-stage records.
- Existing `project.json` remains valid and readable.

### Match workspace truth

Add a separate persisted workspace record rather than expanding `Project` into a match container.

Required top-level workspace fields:

- `match_id`
- `name`
- `description`
- `created_at`
- `updated_at`
- `stage_order`
- `stage_entries`
- `shared_defaults`
- `match_output_profiles`
- `ui_state`
- `schema_version`

### Stage entry fields inside a workspace

- `stage_id`
- `relative_project_path`
- `display_name`
- `stage_number`
- `status`
- `override_values`
- `last_reviewed_at`
- `source_media_present`

### Output profile model

Use `output_profile` as the SplitShot-native schema name in place of competitor naming.

Required fields:

- `output_id`
- `scope_type`
- `scope_id`
- `profile_name`
- `profile_kind`
- `frame_profile`
- `metric_caption_preset`
- `lead_in_card`
- `brand_mark`
- `subject_track_crop`
- `visibility_recipe`
- `retained_proxy_id`
- `last_rendered_at`

## Exact Disk Layout

### Single-stage bundle

- `<project folder>/project.json`
- `<project folder>/Input/`
- `<project folder>/CSV/`
- `<project folder>/Output/`
- `<project folder>/Markers/`

### Match workspace bundle

- `<workspace folder>/workspace.json`
- `<workspace folder>/Stages/<stage_id>/project.json`
- `<workspace folder>/Stages/<stage_id>/Input/`
- `<workspace folder>/Stages/<stage_id>/CSV/`
- `<workspace folder>/Stages/<stage_id>/Output/`
- `<workspace folder>/Stages/<stage_id>/Markers/`
- `<workspace folder>/Output/Match/`

### Performance Library store

- `~/.splitshot/library/...` as defined in [03-performance-library-spec.md](03-performance-library-spec.md)

## Exact Compatibility Rules

- Legacy project folders remain readable with no pre-conversion.
- When a legacy single-stage project is added to a match workspace, its `Project.id` becomes the workspace `stage_id`.
- If a legacy project lacks a stable id, one is generated once, saved back into `project.json`, and reused thereafter.
- New workspace metadata must not change the meaning of existing stage analysis fields.

## Inheritance Serialization Contract

- App defaults continue to live in `~/.splitshot/settings.json`.
- Folder defaults continue to live in `splitshot.conf`.
- Match-shared defaults live in `workspace.json`.
- Stage-local overrides live only in `workspace.json.stage_entries[].override_values`.
- Stage `project.json` files do not duplicate inherited workspace defaults.

Resolution order for eligible settings:

1. stage override
2. match shared default
3. folder default
4. app default
5. domain default

## Required Browser-State Field Names

The data model must support these state keys:

- `editor_scope`
- `active_match_id`
- `active_stage_id`
- `workspace_stage_entries`
- `workspace_shared_defaults`
- `workspace_override_summary`
- `output_profiles`
- `library_summary`
- `proxy_summary`

## Required Tests And Proof

- serialization round-trip for new workspace model
- compatibility open for legacy `project.json`
- deterministic inheritance resolution test over all five layers
- output profile persistence without stage-truth duplication
- proxy invalidation keyed by `generated_from_truth_hash`

## Compatibility And Regression Contract

### Legacy single-stage invariants

The following behaviors are frozen and must not regress:

- a valid single-stage project folder still opens through existing `project.json` handling
- `Project.id` remains stable across save/load
- current project asset subdirectories remain valid
- stage-only workflows do not require workspace metadata

### Output-profile expansion invariants

Adding `output_profile` support must not:

- rewrite stage timing truth
- rewrite stage scoring truth
- require all exports to migrate immediately to new profile records
- break the current default single-output export path

### Regression proof expectations

Before widening tests, the implementation must prove:

- legacy project round-trip passes
- output-profile serialization does not duplicate stage truth
- retained proxy hash invalidation is deterministic
