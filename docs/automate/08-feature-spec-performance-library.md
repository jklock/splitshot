# Performance Library Feature Specification

Performance Library is the separate long-term record and playback surface.

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

### 4. Retained proxy playback

Every useful library record should expose a small retained review proxy that can be played without reopening the full workspace first.

### 5. Jump to editor

From any useful record, the user should be able to:

- jump to Single Video for one stage
- jump to Multi Video for a match workspace

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

## Historical Query Surface

The query model must support questions like:

- show reload performance over the last 100 stages
- compare first-shot reaction across two matches
- open the video associated with a specific outlier result
- compare the same stage name across many events when stage metadata allows it

## Playback Behavior

Opening a record should:

1. show library summary and key metrics
2. show the retained review proxy
3. allow jump to the appropriate editor scope

## Technical Acceptance Criteria

- Metrics are queryable without reopening projects manually.
- Retained review proxies open quickly from the library.
- Library records link deterministically back to stage or match workspaces.
- The system can answer "first match vs 100th match" style questions directly from indexed data.

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
- `editor_target`
- `truth_hash`

## Exact Query Surface

The library UI and API must support:

- list recent stages
- list recent matches
- filter by stage, match, date, discipline, competitor
- sort by date or one normalized metric
- open a specific stage or match editor target

## Required Routes

- `/api/library/list`
- `/api/library/filter`
- `/api/library/stage/open`
- `/api/library/match/open`
- `/api/library/proxy/open`
- `/api/library/proxy/refresh`

## Refresh And Proxy Contract

- Library record writes are triggered by accepted save events, not every in-progress edit.
- Proxy refresh is required when a visible review-video outcome changes:
  - timing truth
  - score summary overlay
  - metric caption preset
  - lead-in card
  - brand mark
  - output profile selected as retained-review source
- The library must store the last accepted `truth_hash` and compare it to the active proxy hash before marking a proxy current.

## Failure States

- If the library record exists but editor linkage is broken, the UI shows history and marks reopen unavailable.
- If the proxy file is missing, the UI shows metrics and exposes regenerate.
- If the source project folder is gone, the library record remains queryable.

## Required Tests And Proof

- stage and match library record write
- filter query behavior
- proxy stale detection
- jump-to-editor resolution for both stage and match targets
