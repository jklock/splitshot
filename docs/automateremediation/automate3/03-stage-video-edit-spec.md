# Stage Video Edit Spec

Stage Video Edit is the deep editor for one stage. It should evolve from the current editor, not be replaced by a shallow dashboard.

## Preserve

The following capabilities remain available inside Stage Video Edit:

- Project
- PiP
- Score
- Splits
- Markers
- Overlay
- Review
- Export
- Metrics
- ShotML
- Settings

They should be grouped and presented as Stage editing tools, not as top-level product navigation.

## Required Layout

Stage Video Edit must have:

- stage context header with project/stage/match status
- primary preview area
- timeline and waveform area
- inspector/tool area
- output/profile area integrated into Stage, not a global automation strip
- clear no-media empty state
- loaded-media state with real preview/timeline/controls
- workspace-stage state when opened from Match.

## Required Workflows

- import/open stage media
- review timing and shots
- edit scoring
- configure overlays and markers
- configure review visibility
- manage output profiles
- choose retained review source
- preview render plan
- render stage output
- add and manage multi-angle clips
- line up angles
- assign camera jobs
- balance audio
- override smart cuts
- create or attach to Match without forced navigation
- return to Match when opened from Match.

## Render Plan Target Contract

The target UI needs a read-only render-plan preview before the user confirms render. The implementation agent must verify the current `controller.output_profile_render(output_id)` payload before wiring this panel. If the current payload is insufficient, update backend/controller tests first.

Target render-plan content:

- `steps`: ordered list of pipeline steps, such as trim dead time, apply overlay, encode output
- `estimated_duration_ms`: approximate render time where available
- `output_path`: target file path
- `dimensions`: `{width, height}`
- `frame_rate`: target frame rate
- `has_warnings`: boolean for source/settings conflicts
- `warnings`: user-readable warning list when `has_warnings` is true

The UI must label missing fields as unavailable rather than inventing values.

## Multi-Angle Requirements

PiP and multi-angle interactions must be stable enough for visual sync:

- small drift uses bounded playback-rate correction
- hard seek only on explicit boundaries or large drift
- dragging uses local frame geometry and commits after settle
- no route calls on every pointer move.

## Acceptance

Stage is acceptable only when:

- existing editor flows still work
- output/multi-angle/export workflows feel native to Stage
- empty and loaded screenshots prove professional hierarchy
- Match attachment and return behavior are tested
- no user has to understand backend routes to use the view.
