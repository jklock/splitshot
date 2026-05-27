# Stage Video Edit Feature Specification

Stage Video Edit is the focused one-stage editor.

## Current Features To Preserve

- primary video import
- beep and shot detection
- manual timing correction
- scoring and PracticeScore context
- overlays, review text, markers, and metrics
- current export settings and output control
- PiP / secondary video
- waveform editor
- ShotML pipeline
- all existing tool panes (Project, PiP, Score, Splits, Markers, Overlay, Review, Export, Metrics, ShotML)

## New Feature Goals

### 1. Trim Dead Time (formerly Run Window)

Add a named workflow that:

- detects the effective stage window
- trims dead time before and after the run
- lets the user set lead-in and tail padding
- produces a clean output variant quickly
- shows a visual preview of the trim boundaries on the waveform

Layman label: **"Trim Dead Time"**

### 2. Shot Data Overlay (formerly Metric Captions)

Add output presets that derive directly from reviewed truth and can display:

- shot count
- split times
- cumulative time
- first-shot reaction
- best split
- score per shot

This should not replace deep overlay controls.
It should provide a faster path to useful outputs.

Layman label: **"Shot Data on Screen"**

### 3. One-run many-output variants

Stage Video Edit must support multiple named outputs from the same reviewed run, for example:

- dense technical review cut
- clean recap cut
- vertical social-style cut
- branded title-card cut
- portrait crop cut

### 4. Video Shape (formerly Frame Profiles)

Stage Video Edit should support output recipes for:

- source ratio
- `16:9`
- `9:16`
- `1:1`
- `4:5`

Layman label: **"Video Shape"**

### 5. Keep Shooter in Frame (formerly Subject Track Crop)

For non-source aspect ratios, Stage Video Edit should support tracked reframing.

Scope:

- choose subject target (manual click or auto-detect)
- track crop center across frames
- allow re-track and reset
- persist per output variant
- show a preview of the crop area

Layman label: **"Keep Shooter in Frame"**

### 6. Opening Title (formerly Lead-In Card)

Add title-card configuration as part of output variants:

- match name
- date
- shooter identity
- optional logo
- chosen title-card style
- preview the title card before rendering

Layman label: **"Opening Title"**

### 7. Your Logo (formerly Brand Mark)

Add watermark configuration as part of output variants:

- text or image watermark
- position
- opacity
- scale or sizing
- padding
- preview on the video before rendering

Layman label: **"Your Logo"**

### 8. Smart Angle Switching (formerly Stage Mix / Angle Director)

For multi-angle stages, provide auto-cut guidance:

- analyze motion and audio across angles
- suggest cut points
- show suggested cuts on the timeline
- let the user override any cut
- preview the auto-directed output

Layman label: **"Smart Angle Switching"**

### 9. Line Up Angles (formerly Angle Align)

For same-stage dual-angle comparison:

- auto-sync by beep
- manual sync nudge
- show both angles with synchronized playhead
- support layout options: side-by-side, picture-in-picture, full-screen swap

Layman label: **"Line Up Angles"**

### 10. Camera Jobs (formerly Angle Roles)

Tag each angle with its purpose:

- `Primary` — main view
- `Follow` — following the shooter
- `Static` — fixed camera
- `Detail` — close-up of hands or gear

Used by Smart Angle Switching to make better cut decisions.

Layman label: **"Camera Jobs"**

### 11. Audio Balance (formerly Audio Mix Lanes)

Control audio contribution per angle:

- mute/unmute each angle
- adjust gain per angle
- select primary audio source
- preview mixed audio

Layman label: **"Audio Balance"**

### 12. Override Smart Cuts (formerly Cut Override Plan)

After Smart Angle Switching suggests cuts:

- show all suggested cuts in a list
- let the user accept, reject, or move each cut
- show the final cut plan before rendering
- save the override plan as part of the output profile

Layman label: **"Override Smart Cuts"**

### 13. Multi-Track Waveform

When multiple angles are present, show:

- one waveform track per angle
- color-coded tracks
- synchronized playhead across all tracks
- mute/solo per track
- volume fader per track

### 14. Color-Coded Segments

Auto-label segments of the stage:

- `Moving` — shooter is in motion
- `Static` — shooter is stationary
- `Long Move` — extended movement
- show as colored bands on the waveform
- useful for Smart Angle Switching and review

## Explicit Non-goals For Stage Video Edit

- do not turn this into a generic timeline editor
- do not require social sharing features to validate the mode
- do not replace review truth with output-specific edits
- do not overwhelm the user with too many options at once

## Technical Acceptance Criteria

- Trim Dead Time uses reviewed or draft timing boundaries consistently.
- Shot Data Overlay resolves from authoritative split rows and stage metrics, not duplicate data entry.
- Multiple output variants persist without duplicating stage truth.
- Video Shape, Opening Title, Your Logo, and later Keep Shooter in Frame settings persist per output.
- Retained proxies can be generated from selected Stage Video Edit output variants.
- Smart Angle Switching suggestions are editable and do not rewrite stage truth.
- Line Up Angles sync is accurate to within 50ms.
- Multi-track waveform renders smoothly at 30fps.

## SplitShot-Native Implementation Labels

Use these labels in implementation-facing work:

- `Trim Dead Time`
- `Shot Data Overlay`
- `Output Profiles`
- `Video Shape`
- `Keep Shooter in Frame`
- `Opening Title`
- `Your Logo`
- `Smart Angle Switching`
- `Line Up Angles`
- `Camera Jobs`
- `Audio Balance`
- `Override Smart Cuts`
- `Multi-Track Waveform`
- `Color-Coded Segments`

## Current Repo Seams To Extend

- `src/splitshot/domain/models.py`
- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/browser/server.py`
- `src/splitshot/browser/static/panes/export-pane.js`
- `src/splitshot/export/pipeline.py`
- `src/splitshot/browser/static/components/waveform.js`
- `src/splitshot/browser/static/app.js`

## Exact Feature Contracts

### Trim Dead Time

- derives its window from reviewed start and end timing truth
- allows explicit lead-in and tail padding values
- persists per `output_id`, not on stage truth itself
- if reviewed end timing is unavailable, falls back to draft final shot timing plus configured tail padding
- shows trim boundaries as vertical lines on the waveform
- preview updates in real-time as padding changes

### Shot Data Overlay

- resolve from authoritative split rows and stage metrics
- never allow free-form metric value entry
- may allow visibility toggles and formatting presets only
- persist as part of `OutputProfile.metric_caption_preset`
- preview shows actual data on the video

### Output Profiles

- one stage may own many named `output_id` records
- one profile may be marked as the retained review-video source
- deleting an output profile must not modify stage timing or scoring truth

### Video Shape

Required first-delivery options:

- `source`
- `16:9`
- `9:16`
- `1:1`
- `4:5`

### Keep Shooter in Frame

- first delivery must persist crop intent fields even if advanced tracking is partial
- crop state is output-profile-local
- reset returns to source-centered framing for that output profile only
- shows a draggable crop rectangle on the video preview

### Opening Title

- configurable per output profile
- allowed source fields:
  - match name
  - date
  - shooter identity
  - optional logo path
- does not alter stage truth
- preview shows the title card overlaid on the first frame

### Your Logo

- configurable per output profile
- supports text or image source
- supports position, opacity, padding, and scale fields
- does not alter stage truth
- preview shows the watermark on the video

### Smart Angle Switching

- produces a suggested cut plan for multi-angle review
- suggested cuts are editable
- accepted cut decisions persist in the relevant output profile, not in stage truth
- uses Camera Jobs to weight cut decisions
- preview plays the auto-directed sequence

### Line Up Angles

- applies to same-stage multi-angle alignment only
- stores offset and analyzed-source metadata per clip source
- does not imply match-wide editing
- shows sync accuracy in milliseconds

### Camera Jobs

Required first-delivery role set:

- `primary`
- `follow`
- `static`
- `detail`

### Audio Balance

- persist per clip source inside Stage Composite or Match Recap
- control gain, mute, and selected-primary-audio source
- do not alter saved source media
- shows per-track volume meters in the waveform

### Override Smart Cuts

- shows all suggested cuts in a list with timecodes
- accept/reject/move actions per cut
- final plan persists in output profile
- preview updates after each override

## Required Routes

- `/api/output-profiles/create`
- `/api/output-profiles/update`
- `/api/output-profiles/delete`
- `/api/output-profiles/render`
- `/api/stage/trim-preview`
- `/api/stage/crop-preview`
- `/api/stage/title-preview`
- `/api/stage/watermark-preview`
- `/api/stage/angle-sync`
- `/api/stage/cut-plan`
- `/api/stage/cut-plan/override`

Payloads for create/update must include:

- `scope_type=stage`
- `scope_id=<stage_id>`
- `output_id`
- `profile_name`
- changed profile fields

## UI Behavior And Failure States

- The export UI must separate stage truth from output profile settings visually.
- Missing logo or watermark assets must block only the affected render, not the stage editor.
- An invalid video shape value must be rejected at the API layer.
- If an output profile marked as retained-review source is deleted, the next saved profile must be selected explicitly before proxy refresh resumes.
- Smart Angle Switching failures must show a helpful message, not crash the editor.
- Line Up Angles failures must allow manual sync as fallback.

## Required Tests And Proof

- stage output profile CRUD
- output render with `Trim Dead Time`
- Shot Data Overlay render from reviewed truth
- profile-scoped Opening Title and Your Logo persistence
- retained review-video generation from selected stage output profile
- Smart Angle Switching suggestion generation
- Line Up Angles sync accuracy within 50ms
- Multi-track waveform rendering
- Color-Coded Segment generation
