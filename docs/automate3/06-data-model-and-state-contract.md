# Data Model And State Contract

Automate3 requires explicit state boundaries so the views stay separate while the app remains integrated.

## Required State Concepts

- `active_view`: landing, stage, match, or library
- `active_project`: current stage project identity and path
- `active_match`: current match/workspace identity and path
- `active_stage`: current stage identity and stage-in-match metadata
- `opened_from_match`: whether Stage was opened from Match
- `return_to_match`: availability and target context for returning
- `library_record_id`: selected or reopened historical record
- `output_profiles`: available stage/match output profiles
- `active_output_profile`: selected output recipe
- `stage_clips`: stage-local media/angle clips
- `angle_director_plan`: generated and overridden smart-cut plan
- `export_jobs`: active and completed render/export jobs
- `recent_activity`: recent Stage, Match, and Library items.

## `/api/state`

`/api/state` remains summary-oriented. It may expose:

- active context
- high-level status
- counts and summaries
- flags that tell views what to fetch next.

It must not preload heavy library records, full clip detail, full waveform data, or export logs.

## Dedicated Route Rule

Heavy or view-specific data uses dedicated routes:

- Stage clip detail
- angle director plans
- output profile detail/render plan
- library records and analytics
- export job detail/progress.

## View Retention

View switching must preserve useful local state:

- Match grid selection and scroll position
- Stage active tool where practical
- Library selected record and filters
- pending export progress
- return-to-match target.

## State Integration Rules

The implementation agent must verify the exact current store and controller fields before coding. Target integration:

1. Add `active_view` to `browser_state()` in `src/splitshot/browser/state.py` only if backend ownership is needed; otherwise keep it frontend-local and document why.
2. Add frontend `activeView` to `appStore` with default `landing`.
3. Allowed values are `landing`, `stage`, `match`, and `library`.
4. Derive `opened_from_match` and `return_to_match` from actual controller/workspace state after inspection. Do not assume a `project.workspace_id` field exists without verifying it.
5. Preserve local view state:
   - Match grid scroll and selected stage: `localStorage` key `splitshot.match.gridState`
   - Stage active tool: existing `localStorage` key `splitshot.activeTool`
   - Library selected record and filters: `localStorage` key `splitshot.library.state`
   - Export progress: in-memory only; do not persist across reloads unless a backend job model exists.

If any state field cannot be derived from current controller data, add a narrow backend/state contract test before wiring UI behavior.
