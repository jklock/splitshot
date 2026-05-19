# Performance Library Specification

Performance Library is the durable historical system of record for SplitShot.

## Responsibilities

Performance Library must:

- track everything the user imports or creates with SplitShot over time
- mirror the latest reviewed state of runs and matches
- preserve long-term performance history
- retain lightweight local review-video proxies
- let the user compare historical metrics and reopen relevant work

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

## What Remains External

Performance Library is not required to store:

- all original raw media files
- all full-resolution exports
- all temporary working artifacts

Original source media may remain external.
The library should still record enough linkage to reopen the correct work when source media is available.

## Record Types

### Stage record

Stores the canonical latest state for one reviewed stage.

### Match record

Stores the canonical latest state for one match workspace and its stage relationships.

### Output record

Stores metadata for one output variant.

### Proxy record

Stores metadata for one retained lightweight review proxy.

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

## Historical Comparison Requirements

The library must support queries such as:

- reloads at first match vs 100th match
- first-shot reaction over time
- cumulative stage time over time
- stage-to-stage comparison within one match
- same stage across many matches when metadata allows it

## Playback Model

Opening a historical run from the library should:

1. open a library-specific record view
2. show the retained review proxy
3. show historical metrics and summary data
4. provide a clear jump back into Single Video or Multi Video

## Proxy Model

The retained video artifact is a lightweight review proxy, not the raw original and not necessarily the final polished export.

The proxy must be:

- small enough for long-term retention
- visually useful for recall
- linked to the reviewed truth that produced it

## Canonical Update Rules

Performance Library mirrors the latest reviewed state.

That means:

- editing changes in Single Video or Multi Video update the library record
- meaningful visible truth changes trigger proxy refresh
- library data should not drift behind the accepted state

## Linking Back To The Editor

Each library record must link cleanly to:

- the stage record for Single Video
- the match workspace for Multi Video when applicable

Minimum reopening requirements:

- stable run, stage, and match ids
- enough metadata to resolve the target workspace
- source-media linkage when available

## Acceptance Criteria

- A user can compare historical metrics across time without reopening every project manually.
- A user can play a retained review proxy from the library.
- A user can jump from a library record to the correct stage or match editor context.
- The library always reflects the latest reviewed truth for the saved work.

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
- `~/.splitshot/library/proxies/stages/<stage_id>/<generated_from_truth_hash>.mp4`
- `~/.splitshot/library/proxies/matches/<match_id>/<generated_from_truth_hash>.mp4`

The library is separate from stage and match bundles so it can remain canonical over time even when the user is not browsing old folders manually.

## Exact Update Contract

- Saving reviewed stage truth in `Single Video` refreshes the stage library record for that `stage_id`.
- Saving workspace changes in `Multi Video` refreshes:
  - the workspace library record for that `match_id`
  - any affected stage records whose accepted truth or output metadata changed
- Library refresh is triggered synchronously at accepted save points in first delivery.
- The architecture must reserve a later background refresh seam, but first delivery proof assumes synchronous correctness.

## Required Browser/API Contract

### `/api/state` additions

- `library_summary`
- `library_filters`
- `library_selection`
- `library_reopen_targets`
- `library_proxy_status`

### Required routes

- `/api/library/list`
- `/api/library/filter`
- `/api/library/stage/open`
- `/api/library/match/open`
- `/api/library/proxy/open`
- `/api/library/proxy/refresh`

### Route expectations

- browse routes return lightweight summaries only
- open routes return deterministic reopen targets keyed by stable ids
- proxy refresh returns:
  - target scope
  - active proxy path
  - truth hash
  - refreshed or reused status

## Query And Comparison Contract

The index must answer without reopening project folders:

- stage history by stage name, date, match, discipline, competitor
- longitudinal metric comparisons by normalized metric keys
- cross-match stage comparisons when stage metadata matches
- direct jump from outlier row to stage or match editor target

## Failure Behavior

- Missing source media does not invalidate the library record.
- Missing retained proxy marks the record playable state as unavailable and exposes proxy regeneration.
- Broken editor linkage marks the record as unresolved but keeps historical metrics visible.
- A stale proxy must never be presented as current if `generated_from_truth_hash` does not match the active reviewed truth hash.

## Required Tests And Proof

- library record creation after stage save
- library record refresh after workspace save
- retained proxy invalidation when visible truth changes
- history query test for at least one longitudinal metric
- browser test for jump from library record to correct editor target
