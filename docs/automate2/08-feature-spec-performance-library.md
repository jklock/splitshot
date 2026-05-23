# Performance Library Feature Specification v2

Performance Library is the separate long-term record and playback surface. It is the app's killer feature.

## Core Features

### 1. Historical metric browsing

Users must be able to browse:

- stage history
- match history
- per-run performance summaries
- trends over time

### 2. Cross-match comparisons

Users must be able to compare metrics such as:

- reloads
- transitions
- first-shot reaction
- cumulative time
- score deltas

### 3. Search and filtering

Need filters for any metadata the system can reliably persist, such as:

- match
- stage
- date
- discipline or ruleset
- competitor identity when available
- tags
- personal bests

### 4. Retained proxy playback

Every useful library record should expose a small retained review proxy that can be played without reopening the full workspace first.

### 5. Compressed video archive

Every library record should have an optional compressed video for long-term review.

### 6. PracticeScore archive

PracticeScore CSVs imported into stages are archived in the library for historical reference.

### 7. Jump to editor

From any useful record, the user should be able to:

- jump to Stage Video Edit for one stage
- jump to Match Video Edit for a match workspace

### 8. Performance analytics

The library must provide:

- trend charts for key metrics
- personal best tracking
- outlier detection
- discipline breakdowns
- stage-to-stage comparisons

### 9. Tagging and notes

Users must be able to:

- add tags to any record
- add notes to any record
- filter by tags
- search notes

### 10. Library export

Users must be able to:

- export selected records to CSV
- export selected records to JSON
- generate a PDF report

### 11. Backup and restore

Users must be able to:

- backup the entire library to a single file
- restore the library from a backup file

## Metric Categories

At minimum, the library should support indexing and comparison for:

- reloads
- transitions
- first-shot reaction
- cumulative time
- split summaries
- score outcomes
- penalties and derived deltas

## Rollup Rules

The rollup contract is:

- stage-level only metrics:
  - split list summary
  - shot-by-shot timing detail
  - reload durations
  - transition durations
- match-rollup metrics:
  - cumulative time totals
  - average first-shot reaction
  - total penalties
  - stage-count-normalized summary values
- longitudinal comparison metrics:
  - first-shot reaction
  - cumulative time
  - reload count
  - reload duration summary
  - transition duration summary
  - penalties
  - final score deltas when the ruleset is comparable

## Refresh Model

Performance Library mirrors latest reviewed state.

That means:

- editor truth updates library records
- updated truth refreshes stored metric indexes
- retained proxies live-sync with meaningful visible truth changes
- PracticeScore CSVs are archived on import
- compressed videos are generated on explicit request

## Historical Query Surface

The query model must support questions like:

- show reload performance over the last 100 stages
- compare first-shot reaction across two matches
- open the video associated with a specific outlier result
- compare the same stage name across many events when stage metadata allows it
- show all personal bests
- show all stages tagged "practice" or "match"

## Playback Behavior

Opening a record should:

1. show library summary and key metrics
2. show the retained review proxy
3. show PracticeScore data if available
4. show tags and notes
5. allow jump to the appropriate editor scope

## Analytics Behavior

Opening analytics should:

1. show dashboard tiles (totals, personal bests, recent activity)
2. show trend charts for selected metrics
3. allow metric selection and date range filtering
4. allow comparison between two records
5. highlight outliers

## Technical Acceptance Criteria

- Metrics are queryable without reopening projects manually.
- Retained review proxies open quickly from the library.
- Library records link deterministically back to stage or match workspaces.
- The system can answer "first match vs 100th match" style questions directly from indexed data.
- Analytics charts render in under 1 second.
- Tag and note persistence is immediate.
- Export produces valid files.
- Backup and restore preserve all data.

## Current Repo Seams To Extend

- `src/splitshot/config.py`
- `src/splitshot/domain/models.py`
- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/browser/server.py`

## Exact Record Contract

### Stage library record

Must include:

- `library_record_id`
- `stage_id`
- `match_id`
- `display_name`
- `event_date`
- `discipline`
- `competitor_name`
- `metric_summary`
- `output_profile_refs`
- `active_retained_proxy`
- `archive_id`
- `practiscore_csv_path`
- `tags`
- `notes`
- `personal_bests`
- `editor_target`
- `truth_hash`

### Match library record

Must include:

- `library_record_id`
- `match_id`
- `display_name`
- `event_date`
- `discipline`
- `stage_ids`
- `aggregate_metric_summary`
- `output_profile_refs`
- `active_retained_proxy`
- `archive_id`
- `practiscore_csv_path`
- `tags`
- `notes`
- `editor_target`
- `truth_hash`

## Exact Query Surface

The library UI and API must support:

- list recent stages
- list recent matches
- filter by stage, match, date, discipline, competitor, tags
- sort by date or one normalized metric
- open a specific stage or match editor target
- search notes and tags

## Required Routes

- `/api/library/list`
- `/api/library/filter`
- `/api/library/stage/open`
- `/api/library/match/open`
- `/api/library/proxy/open`
- `/api/library/proxy/refresh`
- `/api/library/archive/create`
- `/api/library/tags/update`
- `/api/library/notes/update`
- `/api/library/analytics/trend`
- `/api/library/analytics/compare`
- `/api/library/export/csv`
- `/api/library/export/json`
- `/api/library/backup/create`
- `/api/library/backup/restore`

## Refresh And Proxy Contract

- Library record writes are triggered by accepted save events, not every in-progress edit.
- Proxy refresh is required when a visible review-video outcome changes:
  - timing truth
  - score summary overlay
  - subtitle preset
  - lead-in card
  - brand mark
  - output profile selected as retained-review source
- The library must store the last accepted `truth_hash` and compare it to the active proxy hash before marking a proxy current.

## Failure States

- If the library record exists but editor linkage is broken, the UI shows history and marks reopen unavailable.
- If the proxy file is missing, the UI shows metrics and exposes regenerate.
- If the archive file is missing, the UI shows metrics and exposes regenerate.
- If the source project folder is gone, the library record remains queryable.
- If the library index is corrupted, the system rebuilds from records on next startup.

## Required Tests And Proof

- stage and match library record write
- filter query behavior
- proxy stale detection
- archive generation and retrieval
- jump-to-editor resolution for both stage and match targets
- analytics computation
- tag and note persistence
- CSV export correctness
- JSON export correctness
- backup and restore round-trip
