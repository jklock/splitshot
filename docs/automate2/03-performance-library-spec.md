# Performance Library Specification v2

Performance Library is the durable historical system of record for SplitShot. It is the app's killer feature.

## Responsibilities

Performance Library must:

- track everything the user imports or creates with SplitShot over time
- mirror the latest reviewed state of runs and matches
- preserve long-term performance history
- retain lightweight local review-video proxies
- store PracticeScore output and stage/match scoring data
- store compressed video archives for long-term recall
- let the user compare historical metrics and reopen relevant work
- provide analytics, trends, and insights
- answer questions like "How has my first-shot reaction improved?"
- be searchable, filterable, and browsable without reopening project folders

## Canonical Contents

Performance Library is authoritative for:

- run identity
- stage identity
- match identity
- imported official context that has been accepted into reviewed records
- measured timing and scoring outcomes
- computed metrics
- output-variant metadata
- retained proxy references
- PracticeScore CSV archives
- compressed video references
- user-added tags and notes

## What Remains External

Performance Library is not required to store:

- all original raw media files (these stay in project folders)
- all full-resolution exports (these stay in project Output folders)
- all temporary working artifacts

Original source media may remain external.
The library should still record enough linkage to reopen the correct work when source media is available.

## Record Types

### Stage record

Stores the canonical latest state for one reviewed stage.

Fields:
- `library_record_id`
- `stage_id`
- `match_id` (nullable)
- `display_name`
- `event_date`
- `discipline`
- `competitor_name`
- `metric_summary` (first-shot reaction, cumulative time, splits, reloads, transitions, penalties, score)
- `output_profile_refs`
- `active_retained_proxy`
- `editor_target`
- `truth_hash`
- `practiscore_csv_path` (path to archived CSV)
- `compressed_video_path` (path to compressed review video)
- `tags` (user-added array)
- `notes` (user-added string)
- `personal_bests` (object of PB flags)

### Match record

Stores the canonical latest state for one match workspace and its stage relationships.

Fields:
- `library_record_id`
- `match_id`
- `display_name`
- `event_date`
- `discipline`
- `stage_ids`
- `aggregate_metric_summary`
- `output_profile_refs`
- `active_retained_proxy`
- `editor_target`
- `truth_hash`
- `practiscore_csv_path`
- `tags`
- `notes`

### Output record

Stores metadata for one output variant.

### Proxy record

Stores metadata for one retained lightweight review proxy.

### Analytics record

Stores pre-computed analytics for fast dashboard rendering.

Fields:
- `analytics_id`
- `competitor_name`
- `metric_key` (e.g., "first_shot_reaction", "cumulative_time")
- `time_series` (array of {date, value, stage_id, match_id})
- `personal_best` (best value and date)
- `trend_direction` (improving, stable, declining)
- `last_updated`

## Indexing Model

Performance Library should index:

- stage name or identifier
- match name or identifier
- date
- discipline or ruleset when known
- competitor identity when known
- score summary
- timing summary
- computed metric summary
- linked output variants
- retained proxies
- tags
- personal bests

## Historical Comparison Requirements

The library must support queries such as:

- reloads at first match vs 100th match
- first-shot reaction over time
- cumulative stage time over time
- stage-to-stage comparison within one match
- same stage across many matches when metadata allows it
- personal bests by metric
- average performance by discipline
- penalty trends over time

## Playback Model

Opening a historical run from the library should:

1. open a library-specific record view
2. show the retained review proxy
3. show historical metrics and summary data
4. show PracticeScore data if available
5. show tags and notes
6. provide a clear jump back into Stage Video Edit or Match Video Edit

## Proxy Model

The retained video artifact is a lightweight review proxy, not the raw original and not necessarily the final polished export.

The proxy must be:

- small enough for long-term retention (target: under 50MB per stage)
- visually useful for recall (target: 720p or lower)
- linked to the reviewed truth that produced it
- regenerated automatically when truth changes

### Compressed Video Archive

In addition to the review proxy, Performance Library stores a compressed video archive:

- target: H.264 MP4 at 480p or 720p
- target bitrate: 2-4 Mbps
- includes the selected output overlay preset
- useful for long-term review without opening the editor
- stored alongside the proxy

## Canonical Update Rules

Performance Library mirrors the latest reviewed state.

That means:

- editing changes in Stage Video Edit or Match Video Edit update the library record
- meaningful visible truth changes trigger proxy refresh
- library data should not drift behind the accepted state
- PracticeScore CSVs are archived on import
- compressed videos are generated on export or explicit "Archive" action

## Linking Back To The Editor

Each library record must link cleanly to:

- the stage record for Stage Video Edit
- the match workspace for Match Video Edit when applicable

Minimum reopening requirements:

- stable run, stage, and match ids
- enough metadata to resolve the target workspace
- source-media linkage when available

## Analytics and Insights

Performance Library must compute and display:

### Dashboard Tiles
- Total stages recorded
- Total matches recorded
- Personal bests count
- Recent activity summary

### Trend Charts
- First-shot reaction over time (line chart)
- Cumulative time over time (line chart)
- Split consistency (box plot or violin chart)
- Reload speed over time (line chart)
- Score trend (line chart)

### Comparison Views
- Side-by-side stage comparison (select two stages, compare all metrics)
- Match summary table (all stages in one match)
- Discipline breakdown (average metrics by discipline)

### Outlier Detection
- Highlight stages where a metric was significantly better or worse than trend
- Suggest stages worth reviewing

## Acceptance Criteria

- A user can compare historical metrics across time without reopening every project manually.
- A user can play a retained review proxy from the library.
- A user can jump from a library record to the correct stage or match editor context.
- The library always reflects the latest reviewed truth for the saved work.
- A user can view trend charts for any indexed metric.
- A user can compare two stages side-by-side.
- A user can add tags and notes to any record.
- A user can export library data to CSV or JSON.
- A user can backup and restore the entire library.

## Current Repo Seams To Extend

- `src/splitshot/config.py`
  - app-level persisted data already lives under `~/.splitshot`.
- `src/splitshot/domain/models.py`
  - stage truth and serialized output metadata originate from the canonical project model.
- `src/splitshot/ui/controller.py`
  - editor mutations and autosave are the correct refresh trigger seam.
- `src/splitshot/browser/state.py`
  - library summaries and navigation state must be added to the browser payload.
- `src/splitshot/browser/server.py`
  - library browse, filter, and reopen routes are additive to the current API surface.

## Exact Storage Contract

Performance Library is stored under:

- `~/.splitshot/library/`

Required layout:

- `~/.splitshot/library/records/stages/<library_record_id>.json`
- `~/.splitshot/library/records/matches/<library_record_id>.json`
- `~/.splitshot/library/records/outputs/<library_record_id>.json`
- `~/.splitshot/library/index/stage_metrics.jsonl`
- `~/.splitshot/library/index/match_metrics.jsonl`
- `~/.splitshot/library/index/search_catalog.json`
- `~/.splitshot/library/index/analytics.json`
- `~/.splitshot/library/proxies/stages/<stage_id>/<generated_from_truth_hash>.mp4`
- `~/.splitshot/library/proxies/matches/<match_id>/<generated_from_truth_hash>.mp4`
- `~/.splitshot/library/archives/stages/<stage_id>/<generated_from_truth_hash>.mp4`
- `~/.splitshot/library/practiscore/<stage_id>/`
- `~/.splitshot/library/tags.json`
- `~/.splitshot/library/backup/manifest.json`

The library is separate from stage and match bundles so it can remain canonical over time even when the user is not browsing old folders manually.

## Exact Update Contract

- Saving reviewed stage truth in `Stage Video Edit` refreshes the stage library record for that `stage_id`.
- Saving workspace changes in `Match Video Edit` refreshes:
  - the workspace library record for that `match_id`
  - any affected stage records whose accepted truth or output metadata changed
- Library refresh is triggered synchronously at accepted save points in first delivery.
- The architecture must reserve a later background refresh seam, but first delivery proof assumes synchronous correctness.
- PracticeScore CSVs are copied to `library/practiscore/` on import.
- Compressed videos are generated on explicit "Archive" action or automatic proxy refresh policy.

## Required Browser/API Contract

### `/api/state` additions

- `library_summary`
- `library_filters`
- `library_selection`
- `library_reopen_targets`
- `library_proxy_status`
- `library_analytics`
- `library_recent_activity`

### Required routes

- `/api/library/list`
- `/api/library/filter`
- `/api/library/stage/open`
- `/api/library/match/open`
- `/api/library/proxy/open`
- `/api/library/proxy/refresh`
- `/api/library/archive/create`
- `/api/library/archive/open`
- `/api/library/tags/update`
- `/api/library/notes/update`
- `/api/library/analytics/trend`
- `/api/library/analytics/compare`
- `/api/library/export/csv`
- `/api/library/export/json`
- `/api/library/backup/create`
- `/api/library/backup/restore`

### Route expectations

- browse routes return lightweight summaries only
- open routes return deterministic reopen targets keyed by stable ids
- proxy refresh returns:
  - target scope
  - active proxy path
  - truth hash
  - refreshed or reused status
- analytics routes return pre-computed or on-demand computed data
- export routes generate downloadable files

## Query And Comparison Contract

The index must answer without reopening project folders:

- stage history by stage name, date, match, discipline, competitor
- longitudinal metric comparisons by normalized metric keys
- cross-match stage comparisons when stage metadata matches
- direct jump from outlier row to stage or match editor target
- personal best queries
- trend analysis

## Failure Behavior

- Missing source media does not invalidate the library record.
- Missing retained proxy marks the record playable state as unavailable and exposes proxy regeneration.
- Missing compressed video marks the archive state as unavailable and exposes archive regeneration.
- If the source project folder is gone, the library record remains queryable.
- If the library index is corrupted, the system must rebuild from records on next startup.

## Required Tests And Proof

- library record creation after stage save
- library record refresh after workspace save
- retained proxy invalidation when visible truth changes
- compressed video generation and retrieval
- history query test for at least one longitudinal metric
- browser test for jump from library record to correct editor target
- analytics computation test
- tag and note persistence test
- export test for CSV and JSON
- backup and restore test
