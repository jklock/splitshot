# Single Video Feature Specification

Single Video is the focused one-stage editor.

## Current Features To Preserve

- primary video import
- beep and shot detection
- manual timing correction
- scoring and PractiScore context
- overlays, review text, markers, and metrics
- current export settings and output control

## New Feature Goals

### 1. Run Window

Add a named Single Video workflow that:

- detects the effective stage window
- trims dead time before and after the run
- lets the user set padding
- produces a clean output variant quickly

### 2. Metric Caption presets

Add output presets that derive directly from reviewed truth and can display:

- shot count
- split times
- cumulative time
- first-shot reaction
- best split

This should not replace deep overlay controls.
It should provide a faster path to useful outputs.

### 3. One-run many-output variants

Single Video must support multiple named outputs from the same reviewed run, for example:

- dense technical review cut
- clean recap cut
- vertical social-style cut
- branded title-card cut

### 4. Frame Profiles

Single Video should support output recipes for:

- source ratio
- `16:9`
- `9:16`
- `1:1`
- `4:5`

### 5. Subject Track Crop

For non-source aspect ratios, Single Video should later support tracked reframing.

Scope:

- choose subject target
- track crop center
- allow re-track and reset
- persist per output variant

### 6. Lead-In Card

Add title-card configuration as part of output variants:

- match name
- date
- shooter identity
- optional logo
- chosen title-card style

### 7. Brand Mark

Add watermark configuration as part of output variants:

- text or image watermark
- position
- opacity
- scale or sizing
- padding

## Explicit Non-goals For Single Video

- do not turn this into a generic timeline editor
- do not require social sharing features to validate the mode
- do not replace review truth with output-specific edits

## Technical Acceptance Criteria

- Run Window uses reviewed or draft timing boundaries consistently.
- Subtitle presets resolve from authoritative timing and metrics, not duplicate data entry.
- Multiple output variants persist without duplicating stage truth.
- Ratio, title-card, watermark, and later portrait-tracking settings persist per output.
- Retained proxies can be generated from selected Single Video output variants.

## SplitShot-Native Implementation Labels

Use these labels in implementation-facing work:

- `Run Window`
- `Metric Captions`
- `Output Profiles`
- `Frame Profiles`
- `Subject Track Crop`
- `Lead-In Card`
- `Brand Mark`

## Current Repo Seams To Extend

- `src/splitshot/domain/models.py`
- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/browser/server.py`
- `src/splitshot/browser/static/panes/export-pane.js`
- `src/splitshot/export/pipeline.py`

## Exact Feature Contracts

### Run Window

- derives its window from reviewed start and end timing truth
- allows explicit lead-in and tail padding values
- persists per `output_id`, not on stage truth itself
- if reviewed end timing is unavailable, falls back to draft final shot timing plus configured tail padding

### Metric Captions

- resolve from authoritative split rows and stage metrics
- never allow free-form metric value entry
- may allow visibility toggles and formatting presets only
- persist as part of `OutputProfile.metric_caption_preset`

### Output Profiles

- one stage may own many named `output_id` records
- one profile may be marked as the retained review-video source
- deleting an output profile must not modify stage timing or scoring truth

### Frame Profiles

Required first-delivery options:

- `source`
- `16:9`
- `9:16`
- `1:1`
- `4:5`

### Subject Track Crop

- first delivery must persist crop intent fields even if advanced tracking is partial
- crop state is output-profile-local
- reset returns to source-centered framing for that output profile only

### Lead-In Card

- configurable per output profile
- allowed source fields:
  - match name
  - date
  - shooter identity
  - optional logo path
- does not alter stage truth

### Brand Mark

- configurable per output profile
- supports text or image source
- supports position, opacity, padding, and scale fields
- does not alter stage truth

## Required Routes

- `/api/output-profiles/create`
- `/api/output-profiles/update`
- `/api/output-profiles/delete`
- `/api/output-profiles/render`

Payloads for create/update must include:

- `scope_type=stage`
- `scope_id=<stage_id>`
- `output_id`
- `profile_name`
- changed profile fields

## UI Behavior And Failure States

- The export UI must separate stage truth from output profile settings visually.
- Missing logo or brand-mark assets must block only the affected render, not the stage editor.
- An invalid frame profile value must be rejected at the API layer.
- If an output profile marked as retained-review source is deleted, the next saved profile must be selected explicitly before proxy refresh resumes.

## Required Tests And Proof

- stage output profile CRUD
- output render with `Run Window`
- caption preset render from reviewed truth
- profile-scoped lead-in and brand-mark persistence
- retained review-video generation from selected stage output profile
